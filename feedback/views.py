import os
import random
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from .forms import FeedbackForm
from .models import DemoClass, Feedback, User, Profile

logger = logging.getLogger(__name__)


# ---------------------------
# Helper: Send email via SendGrid API (HTML + plain-text fallback)
# ---------------------------
def send_otp_email(to_email: str, otp: str, subject: str = "Your verification OTP") -> bool:
    from_email = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")

    plain_body = f"Your OTP code is: {otp}"

    html_content = f"""
    <div style="font-family: Arial; background:#f7f7fb; padding:24px;">
      <div style="max-width:520px; margin:auto; background:white; border-radius:10px; padding:22px;">
        <h2 style="color:#0f172a;">Email Verification</h2>
        <p style="color:#475569;">Use the verification code below.</p>
        <div style="padding:12px 20px; border-radius:8px; background:#f8fafc; font-size:26px; font-weight:700;">
          {otp}
        </div>
      </div>
    </div>
    """

    try:
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=plain_body,
            html_content=html_content
        )

        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            logger.error("SENDGRID_API_KEY missing")
            return False

        sg = SendGridAPIClient(api_key)
        resp = sg.send(message)

        if resp.status_code in (200, 202):
            return True

        logger.error("SendGrid unexpected status: %s", resp.status_code)
        return False

    except Exception as exc:
        logger.exception("Send OTP failed: %s", exc)
        return False

# ---------------------------
# Register with OTP (stores OTP in session, sends via SendGrid)
# ---------------------------
def register_user(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        mobile = request.POST.get("mobile", "").strip()
        password = request.POST.get("password", "")

        if not (name and email and mobile and password):
            messages.error(request, "Please fill all required fields.")
            return redirect("register_user")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register_user")

        otp_code = str(random.randint(100000, 999999))

        # Store in session until verified
        request.session.update({
            "reg_name": name,
            "reg_email": email,
            "reg_mobile": mobile,
            "reg_password": password,
            "reg_otp": otp_code
        })

        # Send OTP via SendGrid API
        sent = send_otp_email(email, otp_code, subject="Verify your email - OTP")
        if not sent:
            messages.error(request, "Failed to send OTP email. Please try again shortly.")
            # Keep the session values so user can retry resend; redirect to verify page
            return redirect("verify_otp")

        messages.success(request, "OTP sent to your email. Please check and verify.")
        return redirect("verify_otp")

    return render(request, "reviews/register.html")


# ---------------------------
# Unified OTP verification (registration + reset)
# ---------------------------
def verify_otp(request):
    reg_email = request.session.get("reg_email")
    reset_email = request.session.get("reset_email")

    if not (reg_email or reset_email):
        messages.error(request, "Session expired or invalid flow. Please start again.")
        return redirect("login_user")

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()

        # Registration flow
        if reg_email and entered_otp and entered_otp == request.session.get("reg_otp"):
            name = request.session.get("reg_name")
            mobile = request.session.get("reg_mobile")
            password = request.session.get("reg_password")

            user = User.objects.create_user(
                username=reg_email,
                email=reg_email,
                first_name=name,
                password=password,
                is_active=True
            )
            Profile.objects.create(user=user, mobile=mobile)

            # clear registration session data
            for key in ["reg_name", "reg_email", "reg_mobile", "reg_password", "reg_otp"]:
                request.session.pop(key, None)

            messages.success(request, "Email verified successfully! Please log in.")
            return redirect("login_user")

        # Forgot password flow
        if reset_email and entered_otp and entered_otp == request.session.get("reset_otp"):
            # OTP ok — redirect to reset password page (which will use reset_email in session)
            return redirect("reset_password")

        messages.error(request, "Incorrect OTP. Please try again.")

    # show which email the OTP was sent to
    email = reg_email if reg_email else reset_email
    return render(request, "reviews/verify_otp.html", {"email": email})


# ---------------------------
# Resend OTP
# ---------------------------
def resend_otp(request):
    reg_email = request.session.get("reg_email")
    reset_email = request.session.get("reset_email")

    if not (reg_email or reset_email):
        messages.error(request, "Session expired. Please try again.")
        return redirect("register_user")

    email = reg_email if reg_email else reset_email
    otp_code = str(random.randint(100000, 999999))

    if reg_email:
        request.session["reg_otp"] = otp_code
    else:
        request.session["reset_otp"] = otp_code

    sent = send_otp_email(email, otp_code, subject="Your new OTP")
    if not sent:
        messages.error(request, "Failed to resend OTP. Try again later.")
    else:
        messages.success(request, "A new OTP has been sent to your email.")

    return redirect("verify_otp")


# ---------------------------
# Forgot password: send OTP
# ---------------------------
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Please enter your email.")
            return redirect("forgot_password")

        if not User.objects.filter(email=email).exists():
            messages.error(request, "Email not registered.")
            return redirect("forgot_password")

        otp_code = str(random.randint(100000, 999999))
        request.session["reset_email"] = email
        request.session["reset_otp"] = otp_code

        sent = send_otp_email(email, otp_code, subject="Password reset OTP")
        if not sent:
            messages.error(request, "Failed to send reset OTP. Try again later.")
            return redirect("forgot_password")

        messages.success(request, "OTP sent to your email.")
        return redirect("verify_otp")

    return render(request, "reviews/forgot_password.html")


# ---------------------------
# Reset password (after OTP verified)
# ---------------------------
def reset_password(request):
    email = request.session.get("reset_email")

    if not email:
        messages.error(request, "No password reset in progress.")
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not password or password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_password")

        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("forgot_password")

        # clear reset session
        request.session.pop("reset_email", None)
        request.session.pop("reset_otp", None)

        messages.success(request, "Password updated successfully. Please log in.")
        return redirect("login_user")

    return render(request, "reviews/reset_password.html", {"email": email})


# ---------------------------
# Login / Logout
# ---------------------------
def login_user(request):
    if request.user.is_authenticated:
        return redirect("demo_class_list")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(username=email, password=password)
        if user:
            login(request, user)
            return redirect("demo_class_list")

        messages.error(request, "Invalid email or password")

    return render(request, "reviews/login.html")


def logout_user(request):
    logout(request)
    return redirect("login_user")


# ---------------------------
# Feedback System
# ---------------------------
@login_required(login_url="login_user")
def demo_class_list(request):
    classes = DemoClass.objects.filter(is_active=True).order_by("date")
    return render(request, "reviews/demo_class_list.html", {"classes": classes})


@login_required(login_url="login_user")
def submit_feedback(request, demo_id):
    demo_class = get_object_or_404(DemoClass, pk=demo_id, is_active=True)

    if request.method == "POST":
        # manual fields (we replaced Django form rendering with manual inputs)
        rating = request.POST.get("rating")
        liked_most = request.POST.get("liked_most", "").strip()
        to_improve = request.POST.get("to_improve", "").strip()
        would_recommend = bool(request.POST.get("would_recommend"))

        # basic validation
        if not rating:
            messages.error(request, "Please provide a rating.")
            return redirect("submit_feedback", demo_id=demo_id)

        # Save feedback
        feedback = Feedback(
            demo_class=demo_class,
            student_name=request.user.first_name or request.user.username,
            student_email=request.user.email,
            rating=int(rating),
            liked_most=liked_most,
            to_improve=to_improve,
            would_recommend=would_recommend,
            source="digital"
        )
        feedback.save()
        return redirect("feedback_thank_you", demo_id=demo_class.id)

    return render(request, "reviews/submit_feedback.html", {
        "demo_class": demo_class
    })


@login_required(login_url="login_user")
def feedback_thank_you(request, demo_id):
    demo_class = get_object_or_404(DemoClass, pk=demo_id)
    return render(request, "reviews/thank_you.html", {"demo_class": demo_class})


@login_required(login_url="login_user")
def feedback_summary(request):
    per_class = DemoClass.objects.annotate(
        feedback_count=Count("feedbacks"),
        avg_rating=Avg("feedbacks__rating")
    ).order_by("-date")

    overall = Feedback.objects.aggregate(
        total_feedback=Count("id"),
        avg_rating=Avg("rating"),
    )

    return render(request, "reviews/feedback_summary.html", {
        "per_class": per_class,
        "overall": overall,
    })



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db.models import Avg, Count
from django.core.mail import send_mail
import random

from .forms import FeedbackForm
from .models import DemoClass, Feedback, User, Profile, Trainer

# ----------------------
# Registration with OTP
# ----------------------

def register_user(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        mobile = request.POST.get("mobile")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register_user")

        otp_code = str(random.randint(100000, 999999))

        # Store temporarily in session
        request.session["reg_name"] = name
        request.session["reg_email"] = email
        request.session["reg_mobile"] = mobile
        request.session["reg_password"] = password
        request.session["reg_otp"] = otp_code

        send_mail(
            "Verify Email OTP",
            f"Your OTP is: {otp_code}",
            None,
            [email],
            fail_silently=False,
        )
        print("OTP sent to:", email, otp_code)

        return redirect("verify_otp")

    return render(request, "reviews/register.html")


# ----------------------
# Unified OTP Verification
# ----------------------

def verify_otp(request):
    reg_email = request.session.get("reg_email")
    reset_email = request.session.get("reset_email")

    if not (reg_email or reset_email):
        return redirect("login_user")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        # Registration OTP
        if reg_email and entered_otp == request.session.get("reg_otp"):
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

            for key in ["reg_name","reg_email","reg_mobile","reg_password","reg_otp"]:
                request.session.pop(key, None)

            messages.success(request, "Email verified successfully!")
            return redirect("login_user")

        # Forgot password OTP
        if reset_email and entered_otp == request.session.get("reset_otp"):
            return redirect("reset_password")

        messages.error(request, "Incorrect OTP")

    email = reg_email if reg_email else reset_email
    return render(request, "reviews/verify_otp.html", {"email": email})


# ----------------------
# Resend OTP
# ----------------------

def resend_otp(request):
    reg_email = request.session.get("reg_email")
    reset_email = request.session.get("reset_email")

    if not (reg_email or reset_email):
        messages.error(request, "Session expired. Please register again.")
        return redirect("register_user")

    email = reg_email if reg_email else reset_email
    otp_code = str(random.randint(100000, 999999))

    if reg_email:
        request.session["reg_otp"] = otp_code
    else:
        request.session["reset_otp"] = otp_code

    send_mail(
        "New OTP Code",
        f"Your new OTP is: {otp_code}",
        None,
        [email],
        fail_silently=False,
    )
    messages.success(request, "A new OTP has been sent.")
    return redirect("verify_otp")


# ----------------------
# Forgot Password OTP Flow
# ----------------------

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not User.objects.filter(email=email).exists():
            messages.error(request, "Email not registered.")
            return redirect("forgot_password")

        otp_code = str(random.randint(100000, 999999))
        request.session["reset_email"] = email
        request.session["reset_otp"] = otp_code

        send_mail(
            "Password Reset OTP",
            f"Your OTP is: {otp_code}",
            None,
            [email],
            fail_silently=False,
        )

        return redirect("verify_otp")

    return render(request, "reviews/forgot_password.html")


def reset_password(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_password")

        user = User.objects.get(email=email)
        user.set_password(password)
        user.save()

        request.session.pop("reset_email", None)
        request.session.pop("reset_otp", None)

        messages.success(request, "Password updated! Please log in.")
        return redirect("login_user")

    return render(request, "reviews/reset_password.html", {"email": email})


# ----------------------
# Login / Logout
# ----------------------

def login_user(request):
    if request.user.is_authenticated:
        return redirect("demo_class_list")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(username=email, password=password)

        if user:
            login(request, user)
            return redirect("demo_class_list")

        messages.error(request, "Invalid email or password")

    return render(request, "reviews/login.html")


def logout_user(request):
    logout(request)
    return redirect("login_user")


# ----------------------
# Feedback System
# ----------------------

@login_required(login_url="login_user")
def demo_class_list(request):
    classes = DemoClass.objects.filter(is_active=True).order_by("date")
    return render(request, "reviews/demo_class_list.html", {"classes": classes})


@login_required(login_url="login_user")
def submit_feedback(request, demo_id):
    demo_class = get_object_or_404(DemoClass, pk=demo_id, is_active=True)

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.demo_class = demo_class
            feedback.student_name = request.user.first_name
            feedback.student_email = request.user.email
            feedback.source = "digital"
            feedback.save()
            return redirect("feedback_thank_you", demo_id=demo_class.id)

    form = FeedbackForm()
    return render(request, "reviews/submit_feedback.html", {
        "demo_class": demo_class,
        "form": form
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

    return render(request, "reviews/feedback_summary.html",
                  {"per_class": per_class, "overall": overall})




# Create your views here.
import django.core.exceptions
import settings
from accounts.forms import UserPasswordResetForm
from amcat.models import AmCAT
from amcat.models import ArticleSet
from amcat.models.authorisation import ROLE_PROJECT_READER
from amcat.tools.usage import log_request_usage
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth import signals
from django.contrib.auth.views import password_reset, password_reset_confirm
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from navigator.forms import AddUserForm, AddUserFormWithPassword
from navigator.utils.auth import create_user


def _login(request, error, username, announcement):
    """
    Render shortcut
    """
    allow_anonymous = not settings.REQUIRE_LOGON
    allow_register = settings.ALLOW_REGISTER

    if allow_anonymous:
        
        featured_sets = [(aset, aset.project.get_role_id(user=request.user) >= ROLE_PROJECT_READER)
                         for aset in ArticleSet.objects.filter(featured=True)]
    
    return render(request, "accounts/login.html", locals())

def _redirect_login(request):
    """
    Redirect a successful login
    """
    next1 = request.GET.get("next")
    if next1 is not None:
        return redirect(next1)

    # Redirect to frontpage
    return redirect("navigator:index")


def login(request):
    """
    Try to log a user in. If method is GET, show empty login-form
    """
    if not request.user.is_authenticated() and request.user.is_active:
        # User already logged in
        return _redirect_login(request)

    system = AmCAT.get_instance()
    announcements = [system.server_warning, system.global_announcement]

    announcement = "<hr/>".join(a for a in announcements if a is not None)

    if request.method == "POST":
        username = request.POST.get("username")
        passwd = request.POST.get("password")

        user = authenticate(username=username, password=passwd)

        if user is None or not user.is_active:
            # Credentials wrong or account disabled
            return _login(request, True, username, announcement)

        # Credentials OK, log user in
        auth_login(request, user)
        signals.user_logged_in.send(sender=user.__class__, request=request, user=user)

        log_request_usage(request, "account" ,"login")
        return _redirect_login(request)

    # GET request, send empty form
    return _login(request, False, None, announcement)

def logout(request):
    log_request_usage(request, "account" ,"logout")
    auth_logout(request)
    signals.user_logged_out.send(sender=request.user.__class__, request=request, user=request.user)

    return redirect(login)

def register(request):
    """
    Let the user fill in a registration form or process such a form.
    """

    if not settings.ALLOW_REGISTER:
        
        raise django.core.exceptions.PermissionDenied("Please use the admin dashboard to create users") 
        
    form_class = AddUserForm if settings.REGISTER_REQUIRE_VALIDATION else AddUserFormWithPassword
    form = form_class(request, data=request.POST or None)

    user = None
    if form.is_valid():
        user = create_user(
            form.cleaned_data['username'],
            form.cleaned_data['first_name'],
            form.cleaned_data['last_name'],
            form.cleaned_data['email'],
            password=form.cleaned_data.get('password'),
        )

        log_request_usage(request, "account" ,"register")
        if not settings.REGISTER_REQUIRE_VALIDATION:
            new_user = authenticate(username=user.username,
                                    password=form.cleaned_data['password'])
            auth_login(request, new_user)
            return HttpResponseRedirect("/")
        
    return render(request, "accounts/register.html", locals())

def recover(request):
    """
    Reset password based on email address or username.

    Send email to user.
    """
    return password_reset(request,
            template_name="accounts/recover.html",
            email_template_name="accounts/reset_email.html",
            subject_template_name="accounts/reset_subject.txt",
            password_reset_form=UserPasswordResetForm,
            post_reset_redirect=reverse(recover_requested)
    )

def recover_requested(request):
    return render(request, "accounts/recover_requested.html")

def recover_confirm(request, uidb64, token):
    return password_reset_confirm(request,
            uidb64=uidb64, token=token,
            template_name="accounts/recover_confirm.html",
            post_reset_redirect=reverse(login))

# Create your views here.
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth import signals
from django.contrib.auth.views import password_reset, password_reset_confirm

from accounts.forms import UserPasswordResetForm
from navigator.forms import AddUserForm
from navigator.utils.auth import create_user

from amcat.models.user import Affiliation
from amcat.models.authorisation import Role

def _login(request, error, username):
    """
    Render shortcut
    """
    return render(request, "accounts/login.html",
        dict(error=error, username=username)
    )

def _redirect_login(request):
    """
    Redirect a successful login
    """
    next1 = request.REQUEST.get("next")
    if next1 is not None:
        return redirect(next1)

    # Redirect to frontpage
    return redirect("navigator.views.report.index")


def login(request):
    """
    Try to log a user in. If method is GET, show empty login-form
    """
    if not request.user.is_authenticated() and request.user.is_active:
        # User already logged in
        return _redirect_login(request)

    if request.method == "POST":
        username = request.POST.get("username")
        passwd = request.POST.get("password")

        user = authenticate(username=username, password=passwd)

        if user is None or not user.is_active:
            # Credentials wrong or account disabled
            return _login(request, True, username)

        # Credentials OK, log user in
        auth_login(request, user)
        signals.user_logged_in.send(sender=user.__class__, request=request, user=user)
        return _redirect_login(request)

    # GET request, send empty form
    return _login(request, False, None)

def logout(request):
    auth_logout(request)
    signals.user_logged_out.send(sender=request.user.__class__, request=request, user=request.user)
    return redirect(login)

def register(request):
    """
    Let the user fill in a registration form or process such a form. 
    """
    form = AddUserForm(request, data=request.POST or None)

    del form.fields['role']
    del form.fields['affiliation']

    user = None
    if form.is_valid():
        user = create_user(
            form.cleaned_data['username'],
            form.cleaned_data['first_name'],
            form.cleaned_data['last_name'],
            form.cleaned_data['email'],
            Affiliation.objects.all()[0],
            form.cleaned_data['language'],
            Role.objects.get(id=1)
        )
        
        form = AddUserForm(request)

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

def recover_confirm(request, uidb36, token):
    return password_reset_confirm(request,
            uidb36=uidb36, token=token,
            template_name="accounts/recover_confirm.html",
            post_reset_redirect=reverse(login))


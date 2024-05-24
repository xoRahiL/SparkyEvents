import datetime
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from .forms import *
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect


# Create your views here.


def index(request):
    return render(request, 'index.html')


def workhand_register(request):
    cat = WorkhandCategory.objects.all()
    if request.method == 'POST':
        try:
            fname = request.POST['fname'].strip()
            lname = request.POST['lname'].strip()
            username = request.POST['username'].strip()
            email = request.POST['email'].strip()
            password = request.POST['password'].strip()
            category1 = request.POST['category'].strip()
            propic = request.FILES['propic']

            wc = WorkhandCategory.objects.get(id=category1)

            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists !')
                raise ValidationError('Username already exists')

            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists !')
                raise ValidationError('Email already exists')

            if len(username) > 10:
                messages.error(request, 'Username should not be greater than 10 characters !')
                raise ValidationError('Username too long')

            if not username.isalnum():
                messages.error(request, 'Username should be alpha-numeric only !\n'
                                        'No spaces or characters allowed.')
                raise ValidationError('Username not alpha-numeric')

            myuser = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            myuser.first_name = fname
            myuser.last_name = lname
            myuser.save()

            w = Workhand(
                user=myuser,
                workhand_category=wc,
                profile_pic=propic
            )
            w.save()

            # Email
            subject = "Welcome to Sparky Events !"
            message = (f"Hello, {myuser.first_name}\n\n\n"
                       f"We'd like to welcome you to SparkyEvents\n"
                       f"And Thank you for joining Us\n"
                       f"With Sparky Events, you can get Event managing job\n"
                       f"So go ahead and start your WorkHand journey\n\n\n"
                       f"And do hesitate to get in touch if you have any questions then\n"
                       f"Just contact Us !\n\n\n\n"
                       f"Thank you from\n"
                       f"-SparkyEvents")
            from_email = settings.EMAIL_HOST_USER
            to_email = myuser.email
            send_mail(subject, message, from_email, [to_email], fail_silently=True)

            messages.success(request, 'You have Successfully Registered.\n'
                                      'You can now Login !')

            return redirect('/workhandlogin/')
        except ValidationError:
            pass

    return render(request, 'workdas/workhand_login.html', {'cat': cat})


def workhand_login(request):
    cat = WorkhandCategory.objects.all()
    if request.method == 'POST':
        username = request.POST['username'].strip()
        password = request.POST['password'].strip()

        try:
            Workhand.objects.get(user__username=username)
        except ObjectDoesNotExist:
            messages.error(request, 'Invalid Username or Password !')
            return redirect('/workhandlogin/')

        myuser = authenticate(username=username, password=password)
        if myuser is not None:
            login(request, myuser)
            messages.success(request, "Successfully Logged In !")

            # Email
            subject = "Login Alert"
            message = (f"Hello, {myuser.first_name}\n\n\n"
                       f"Your account has been Loggen In successfully.\n\n\n\n\n"
                       f"Thank you from\n"
                       f"-SparkyEvents")
            from_email = settings.EMAIL_HOST_USER
            to_email = myuser.email
            send_mail(subject, message, from_email, [to_email], fail_silently=True)

            return redirect('/workhanddashboard/')
        else:
            messages.error(request, "Log In Failed !")
            return redirect('/workhandlogin/')

    return render(request, 'workdas/workhand_login.html', {'cat': cat})


def workhand_forget(request):
    return render(request, 'workdas/workhand_forget.html')


def workhand_dashboard(request):
    u = request.user.id
    wu = Workhand.objects.get(user=u)

    eh = EventHistory.objects.filter(workhand_id=wu)[:5]

    ap = WorkhandApplications.objects.filter(workhand_id=wu)

    # w = Workhand.objects.all()    'w': w,
    return render(request, 'workdas/workhand_dashboard.html', {'wu': wu, 'eh': eh, 'ap': ap})


def workhand_profile(request):
    u = request.user.id
    # print(u)
    wu = Workhand.objects.get(user=u)
    # print(wu)

    category = WorkhandCategory.objects.all().order_by('category')

    if request.method == 'POST':
        propic = request.FILES['propic']
        username = request.POST['username']
        fname = request.POST['fname']
        lname = request.POST['lname']
        email = request.POST['email']
        contact = request.POST['contact']
        address = request.POST['address']
        state = request.POST['state']
        city = request.POST['city']
        category1 = request.POST['category']

        w = User.objects.get(id=u)
        w.username = username
        w.first_name = fname
        w.last_name = lname
        w.email = email
        if propic is not None:
            wu.profile_pic = propic
        wu.address = address
        wu.contact = contact
        wu.state = state
        wu.city = city

        wc = WorkhandCategory.objects.get(id=category1)
        wu.workhand_category = wc

        w.save()
        wu.save()

    return render(request, 'workdas/workhand_profile.html', {'wu': wu, 'cat': category})


def search_events(request):
    events = Event.objects.all()
    u = request.user.id
    # print(u)
    wu = Workhand.objects.get(user=u)
    # print(wu)

    return render(request, 'workdas/search_events.html', {'events': events, 'wu': wu})


def apply_for_event(request, id):
    u = request.user.id
    # print(u)
    wu = Workhand.objects.get(user=u)
    # print(wu)

    applied_event = Event.objects.get(id=id)

    if WorkhandApplications.objects.filter(workhand=wu, to_company=applied_event.company_id,
                                           event=applied_event).exists():
        messages.error(request, 'Already applied check your Application if it is approved !')
        return redirect('/searchevents/')

    application = WorkhandApplications(
        workhand=wu,
        to_company=applied_event.company_id,
        event=applied_event,
    )
    application.save()

    messages.success(request, "Successfully Applied ! You can check Application status in your Approved Applications.")

    return redirect('/searchevents/')


def approved(request):
    user = request.user.id
    wu = Workhand.objects.get(user=user)

    app = WorkhandApplications.objects.filter(workhand=wu)

    return render(request, 'workdas/approved_applications.html', {'app': app, 'wu': wu})


def event_completed(request, id):
    u = request.user.id
    wu = Workhand.objects.get(user=u)

    workhand_application = WorkhandApplications.objects.get(id=id)

    eid = workhand_application.event.id

    e = Event.objects.get(id=eid)

    event_hist = EventHistory(
        event_name=e.event_name,
        description=e.description,
        start_date=e.start_date,
        end_date=e.end_date,
        event_category=e.event_category,
        workhand_category=e.workhand_category,
        workhand_needed=e.workhand_needed,
        payment_range=e.payment_range,
        address=e.address,
        state=e.state,
        city=e.city,
        company_id=e.company_id,
        workhand_id=wu
    )
    event_hist.save()

    workhand_application.delete()

    WorkhandApplications.objects.filter(event=e).delete()

    e.delete()

    return redirect('/approved/')


def workhand_logout(request):
    logout(request)
    messages.success(request, "Successfully Logged Out")
    return redirect('index')


# WORKHAND SIDE ENDS HERE


# COMPANY SIDE STARTS HERE


def company_register(request):
    if request.method == 'POST':
        try:
            company_name = request.POST['cname'].strip()
            username = request.POST['username'].strip()
            email = request.POST['email'].strip()
            password = request.POST['password'].strip()
            propic = request.FILES['propic']

            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists !')
                raise ValidationError('Username already exists')

            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists !')
                raise ValidationError('Email already exists')

            if len(username) > 10:
                messages.error(request, 'Username should not be greater than 10 characters !')
                raise ValidationError('Username too long')

            if not username.isalnum():
                messages.error(request, 'Username should be alpha-numeric only !')
                raise ValidationError('Username not alpha-numeric')

            myuser = User.objects.create_user(username=username, email=email, password=password)
            myuser.first_name = company_name
            myuser.save()

            c = Company(
                user=myuser,
                company_name=company_name,
                profile_pic=propic
            )
            c.save()

            # Email
            subject = "Welcome to Sparky Events !"
            message = (f"Hello, {myuser.first_name}\n\n\n"
                       f"We'd like to welcome you to SparkyEvents\n"
                       f"And Thank you for joining Us\n"
                       f"With Sparky Events, You can get your Events managed faster and better\n"
                       f"So go ahead and start your journey by posting Events that you wanted to Organize\n\n\n"
                       f"And do hesitate to get in touch if you have any questions then\n"
                       f"Just contact Us !\n\n\n\n"
                       f"Thank you from\n"
                       f"-SparkyEvents")
            from_email = settings.EMAIL_HOST_USER
            to_email = myuser.email
            send_mail(subject, message, from_email, [to_email], fail_silently=True)

            messages.success(request, 'You have Successfully Registered.\n'
                                      'You can now Login !')

            return redirect('/companylogin/')
        except ValidationError:
            pass

    return render(request, 'comdas/company_login.html')


def company_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        try:
            Company.objects.get(user__username=username)
        except ObjectDoesNotExist:
            messages.error(request, 'Invalid Username or Password !')
            return redirect('/companylogin/')

        myuser = authenticate(username=username, password=password)
        if myuser is not None:
            login(request, myuser)
            messages.success(request, "Login Successful !")

            # Email
            subject = "Login Alert"
            message = (f"Hello, {myuser.first_name}\n\n\n"
                       f"Your account has been Loggen In successfully.\n\n\n\n\n"
                       f"Thank you from\n"
                       f"-SparkyEvents")
            from_email = settings.EMAIL_HOST_USER
            to_email = myuser.email
            send_mail(subject, message, from_email, [to_email], fail_silently=True)

            return redirect('/companydashboard/')
        else:
            messages.error(request, "Login Failed !")
            return redirect('/companylogin/')

    return render(request, 'comdas/company_login.html')


def company_forget(request):
    return render(request, 'comdas/company_forget.html')


def company_dashboard(request):
    u = request.user.id
    company = Company.objects.get(user=u)

    event = Event.objects.filter(company_id=company)

    eh = EventHistory.objects.filter(company_id=company)[:5]

    return render(request, 'comdas/company_dashboard.html', {'events': event, 'c': company, 'e': eh})


def company_profile(request):
    u = request.user.id
    # print(u)
    cog = Company.objects.get(user=u)
    # print(wu)

    if request.method == 'POST':
        propic = request.FILES['propic']
        username = request.POST['username']
        company_name = request.POST['cname']
        email = request.POST['email']
        contact = request.POST['contact']
        address = request.POST['address']
        state = request.POST['state']
        city = request.POST['city']

        c = User.objects.get(id=u)
        c.username = username
        c.first_name = company_name
        c.email = email
        if propic is not None:
            cog.profile_pic = propic
        cog.contact = contact
        cog.address = address
        cog.state = state
        cog.city = city

        c.save()
        cog.save()

    return render(request, 'comdas/company_profile.html', {'c': cog})


def post_event(request):
    ec = EventsCategory.objects.all().order_by('category')
    wc = WorkhandCategory.objects.all().order_by('category')

    u = request.user.id
    company = Company.objects.get(user=u)

    if request.method == 'POST':
        try:
            event_cat = request.POST['eventCategory']
            ename = request.POST['name']
            desc = request.POST['desc']
            sdate = request.POST['sdate']
            edate = request.POST['edate']
            work_cat = request.POST['workCategory']
            total_workhand = request.POST['totalWorkhandNeeded']
            payment = request.POST['payment']
            address = request.POST['address']
            state = request.POST['state']
            city = request.POST['city']

            u = request.user.id
            cid = Company.objects.get(user=u)

            ec1 = EventsCategory.objects.get(id=event_cat)
            wc1 = WorkhandCategory.objects.get(id=work_cat)

            event = Event(
                event_name=ename,
                description=desc,
                start_date=sdate,
                end_date=edate,
                event_category=ec1,
                workhand_category=wc1,
                workhand_needed=total_workhand,
                payment_range=payment,
                address=address,
                state=state,
                city=city,
                company_id=cid
            )
            event.save()

            return redirect('/manageevent/')

        except Exception as e:
            messages.error(request, e)

    return render(request, 'comdas/post_event.html', {'ec': ec, 'wc': wc, "c": company})


def update_event(request, id):
    ec = EventsCategory.objects.all()
    wc = WorkhandCategory.objects.all()
    ed = Event.objects.get(id=id)

    u = request.user.id
    cid = Company.objects.get(user=u)

    if request.method == 'POST':
        try:
            event_cat = request.POST['eventCategory']
            ename = request.POST['name']
            desc = request.POST['desc']
            sdate = request.POST['sdate']
            edate = request.POST['edate']
            work_cat = request.POST['workCategory']
            total_workhand = request.POST['totalWorkhandNeeded']
            payment = request.POST['payment']
            address = request.POST['address']
            state = request.POST['state']
            city = request.POST['city']

            u = request.user.id
            cid = Company.objects.get(user=u)

            ec1 = EventsCategory.objects.get(id=event_cat)
            wc1 = WorkhandCategory.objects.get(id=work_cat)

            ed.event_name = ename
            ed.description = desc
            ed.start_date = sdate
            ed.end_date = edate
            ed.event_category = ec1
            ed.workhand_category = wc1
            ed.workhand_needed = total_workhand
            ed.payment_range = payment
            ed.address = address
            ed.state = state
            ed.city = city
            ed.company_id = cid

            ed.save()
            return redirect('/manageevent/')

        except Exception as e:
            messages.error(request, e)

    return render(request, 'comdas/update_event.html', {'ec': ec, 'wc': wc, 'ed': ed, 'c': cid})


def delete_event(request, id):
    event = Event.objects.get(id=id)
    event.delete()
    return redirect("/manageevent/")


def manage_event(request):
    u = request.user.id
    cid = Company.objects.get(user=u)

    events = Event.objects.filter(company_id=cid)

    return render(request, 'comdas/manage.html', {'events': events, 'c': cid})


def approve_applications(request):
    user = request.user.id
    cu = Company.objects.get(user=user)

    applications = WorkhandApplications.objects.filter(to_company=cu)

    return render(request, 'comdas/approve_applications.html', {'app': applications, 'c': cu})


def approve_app(request, id):
    user = request.user.id
    cu = Company.objects.get(user=user)

    application = WorkhandApplications.objects.get(id=id)
    application.status = "True"

    application.save()

    return redirect('/approveapplications/')


def reject_app(request, id):
    user = request.user.id
    cu = Company.objects.get(user=user)

    application = WorkhandApplications.objects.get(id=id)

    application.delete()

    return redirect('/approveapplications/')


def workhand_details(request, id):
    wu = Workhand.objects.get(id=id)

    u = request.user.id
    cu = Company.objects.get(user=u)

    return render(request, 'comdas/workhand_details.html', {'wu': wu, 'c': cu})


def company_logout(request):
    logout(request)
    messages.success(request, "Successfully Logged Out")
    return redirect('index')


def workhand_event_history(request):
    u = request.user.id
    wu = Workhand.objects.get(user=u)

    eh = EventHistory.objects.filter(workhand_id=wu)

    return render(request, 'workdas/history.html', {'eh': eh, 'wu': wu})


def company_event_history(request):
    u = request.user.id
    cid = Company.objects.get(user=u)

    eh = EventHistory.objects.filter(company_id=cid)

    return render(request, 'comdas/event_history.html', {'eh': eh, 'c': cid})


def company_feedback(request, id):
    u = request.user.id
    cid = Company.objects.get(user=u)

    if request.method == 'POST':
        eh = EventHistory.objects.get(id=id)

        title = request.POST['title']
        feedback = request.POST['feedback']
        date = datetime.date.today()

        wid = eh.workhand_id.id
        cid = eh.company_id.id

        wu = Workhand.objects.get(id=wid)
        cu = Company.objects.get(id=cid)

        print(cu)
        print(cu.id)

        f = Feedback(
            feedback_title=title,
            feedback=feedback,
            date=date,
            event_id=eh,
            workhand_id=wu,
            company_id=cu
        )
        f.save()

        return redirect('/companyeventhistory/')

    return render(request, 'comdas/feedback.html', {'id': id, 'c': cid})


# def workhand_feedback(request, fid):
#     fb = Feedback.objects.get(id=fid)
#
#     if fb is None:
#         messages.error(request, "No Feedback Received till now !")
#
#     return render(request, 'workdas/feedback_details.html', {'fb': fb})


def workhand_feedback(request, eid):
    eh = EventHistory.objects.get(id=eid)
    try:
        fb = Feedback.objects.get(event_id=eh)
    except Feedback.DoesNotExist:
        messages.error(request, "No Feedback Received with this Event !")
        return redirect('workhandeventhistory')

    return render(request, 'workdas/feedback_details.html', {'fb': fb})

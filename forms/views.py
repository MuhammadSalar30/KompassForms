from django.shortcuts import render,redirect
from django.urls import path
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response 
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password,check_password
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
import json
import os
from collections import Counter, defaultdict
from django.utils.dateparse import parse_date, parse_time
from .models import Response as FormResponse, Answer, AnswerFile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import *
from django.contrib import messages
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SHORT_LEN = 500
MAX_LONG_LEN = 5000
BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".com", ".msi", ".dll", ".scr",
                      ".js", ".vbs", ".ps1", ".sh", ".php", ".py"}


def is_form_owner(request, form):
    return "user_id" in request.session and str(form.owner_id) == request.session["user_id"]


def form_access_status(request, form):
    """Returns 'ok', 'not_found' or 'denied' for the current visitor."""
    owner = is_form_owner(request, form)

    if not form.is_published and not owner:
        return "not_found"

    if form.access_type == "restricted" and not owner:
        email = request.session.get("user_email", "").strip().lower()
        if not email or not form.invites.filter(email=email).exists():
            return "denied"

    return "ok"
# Create your views here.
def Homepage(Request):
    return HttpResponse("Home Page")
def Forms(Request):
    return HttpResponse("Form")
@api_view(['GET'])
def test_api(request):
    return Response({
        "message": "Django is connected to React!"
    })


def homepage_view(request):
    return render(request,"homepage.html")

def register_view(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        department = request.POST.get("department_name")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Check required fields
        if not name or not email or not department or not password or not confirm_password:
            messages.error(request, "All fields are required.")
            return render(request, "signup.html")

        # Check passwords
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "signup.html")

        # Check existing email
        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, "signup.html")

        # Create user
        user = User(
            name=name,
            email=email,
            department=department,
            password=make_password(password),
          
        )

        user.save()

        messages.success(request, "Account created successfully.")

        return redirect("login")

    return render(request, "signup.html")
def settings_view(request):
    return render(request, "settings.html")
def is_admin_session(request):
    return request.session.get("user_role") == "admin"

def login_view(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        remember = request.POST.get("remember")

        # Check required fields
        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, "login.html")

        # Find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid email or password.")
            return render(request, "login.html")

        # Check password
        if not check_password(password, user.password):
            messages.error(request, "Invalid email or password.")
            return render(request, "login.html")

        # Store user information in session
        request.session["user_id"] = str(user.user_id)
        request.session["user_name"] = user.name
        request.session["user_email"] = user.email
        request.session["department"] = user.department
        #request.session["user_role"] = user.role
        request.session["user_role"] = "admin" if user.is_admin else "user"

        # Remember meW
        if remember:
            # Session remains until browser closes or session expires
            request.session.set_expiry(1209600)  # 14 days
        else:
            # Session expires when browser is closed
            request.session.set_expiry(0)
        return redirect("forms_list")
        #return redirect("forms")

    # GET request → display login page
    return render(request, "login.html")
def logout_view(request):
    request.session.flush()
    return redirect("login")
def notify_invite_access(form, invite):

    permission_text = {
        "respond": "respond to",
        "edit": "edit",
        "both": "edit and respond to",
    }.get(invite.permission, "respond to")

    link = f"http://10.1.5.47:8000/f/{form.form_id}/"
    edit_link = f"http://10.1.5.47:8000/forms/edit/{form.form_id}/"

    subject = f"You've been given access to \"{form.title}\""

    body_lines = [
        f'You now have access to {permission_text} the form "{form.title}".',
        "",
    ]

    if invite.can_respond:
        body_lines.append(f"Respond to the form: {link}")
    if invite.can_edit:
        body_lines.append(f"Edit the form: {edit_link}")

    body = "\n".join(body_lines)

    try:
        send_mail(subject, body, None, [invite.email], fail_silently=False)
    except Exception as e:
        print(f"Invite notification failed: {e}")
def forms_list_view(request):

    if "user_id" not in request.session:
        return redirect("login")

    forms = Form.objects.filter(
        owner__user_id=request.session["user_id"]
    ).order_by("-updated_at")

    context = {
        "user_name": request.session.get("user_name"),
        "forms": forms,
    }

    return render(request, "forms_list.html", context)

def forms_view(request, form_id=None):

    if "user_id" not in request.session:
        return redirect("login")
    form = None
    elements_json = "[]"

    if form_id:
        try:
            form = Form.objects.prefetch_related("elements__options").get(form_id=form_id)
        except Form.DoesNotExist:
            return HttpResponse("Form not found.", status=404)

        is_owner = str(form.owner_id) == request.session["user_id"]
        user_email = request.session.get("user_email", "").strip().lower()
        invite = form.invites.filter(email=user_email).first() if not is_owner else None
        can_edit = is_owner or (invite and invite.can_edit)

        if not can_edit:
            return HttpResponse("You don't have permission to edit this form.", status=403)

    form = None
    elements_json = "[]"

    if form_id:

        try:
            form = Form.objects.prefetch_related("elements__options").get(
                form_id=form_id,
                owner__user_id=request.session["user_id"]
            )
        except Form.DoesNotExist:
            return HttpResponse("Form not found.", status=404)

        elements_data = []

        for el in form.elements.order_by("order"):

            elements_data.append({
                "type": el.element_type,
                "id": str(el.element_id),
                "question": el.question_text,
                "questionType": el.question_type,
                "options": [opt.option_text for opt in el.options.all()],
                "required": el.is_required,
                "title": el.title,
                "description": el.description,
                "scaleMin": el.scale_min,
                "scaleMax": el.scale_max,
                "scaleMinLabel": el.scale_min_label,
                "scaleMaxLabel": el.scale_max_label,
                "gridRows": el.grid_rows.splitlines() if el.grid_rows else [],
                "maxFiles": el.max_files,
                "imageUrl": el.image.url if el.image else None,
            })

        import json
        elements_json = json.dumps(elements_data)

    context = {
        "user_name": request.session.get("user_name"),
        "form": form,
        "elements_json": elements_json,
    }

    return render(request, "forms.html", context)
@transaction.atomic
def save_form(request):

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

    if "user_id" not in request.session:
        return JsonResponse({"success": False, "message": "You must be logged in."}, status=401)

    try:
        user = User.objects.get(user_id=request.session["user_id"])

        title = request.POST.get("title", "Untitled Form")
        description = request.POST.get("description", "")
        existing_form_id = request.POST.get("form_id", "").strip()

        if existing_form_id:
            try:
                form = Form.objects.get(form_id=existing_form_id, owner__user_id=request.session["user_id"])
            except Form.DoesNotExist:
                return JsonResponse({"success": False, "message": "Form not found."}, status=404)
            form.title = title
            form.description = description
            form.save()
        else:
            form = Form.objects.create(owner=user, owner_name=user.name, title=title, description=description)

        element_count = int(request.POST.get("element_count", 0))
        kept_element_ids = []

        for index in range(element_count):

            element_type = request.POST.get(f"element_type_{index}")
            if not element_type:
                continue

            is_required = request.POST.get(f"is_required_{index}") == "true"
            db_id = request.POST.get(f"element_db_id_{index}", "").strip()
            uploaded_image = request.FILES.get(f"image_{index}")

            existing_element = None
            if db_id:
                existing_element = FormElement.objects.filter(form=form, element_id=db_id).first()

            field_values = dict(
                order=index,
                element_type=element_type,
                is_required=is_required,
                question_text=request.POST.get(f"question_text_{index}", ""),
                question_type=request.POST.get(f"question_type_{index}", ""),
                title=request.POST.get(f"title_{index}", ""),
                description=request.POST.get(f"description_{index}", ""),
                max_files=int(request.POST.get(f"max_files_{index}", 1) or 1),
                scale_min=request.POST.get(f"scale_min_{index}") or None,
                scale_max=request.POST.get(f"scale_max_{index}") or None,
                scale_min_label=request.POST.get(f"scale_min_label_{index}", ""),
                scale_max_label=request.POST.get(f"scale_max_label_{index}", ""),
                grid_rows=request.POST.get(f"grid_rows_{index}", ""),
            )

            if existing_element:
                for key, value in field_values.items():
                    setattr(existing_element, key, value)

                if uploaded_image:
                    existing_element.image = uploaded_image
                # agar nayi image upload nahi hui, purani image chhuti hui nahi, wahi rehti hai

                existing_element.save()
                element = existing_element
                element.options.all().delete()
            else:
                element = FormElement.objects.create(image=uploaded_image, form=form, **field_values)

            kept_element_ids.append(element.element_id)

            options = request.POST.getlist(f"options_{index}")
            for opt_index, option_text in enumerate(options):
                if option_text.strip():
                    ElementOption.objects.create(element=element, option_text=option_text, order=opt_index)

        # jo elements pehle thе lekin ab sections array mein nahi hain, wo user ne delete kiye thе
        if existing_form_id:
            form.elements.exclude(element_id__in=kept_element_ids).delete()

        return JsonResponse({"success": True, "message": "Form saved successfully.", "form_id": str(form.form_id)})

    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": "User not found."}, status=404)

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@transaction.atomic
def publish_form(request, form_id):

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

    if "user_id" not in request.session:
        return JsonResponse({"success": False, "message": "You must be logged in."}, status=401)

    try:
        form = Form.objects.get(form_id=form_id, owner__user_id=request.session["user_id"])
    except Form.DoesNotExist:
        return JsonResponse({"success": False, "message": "Form not found."}, status=404)

    action = request.POST.get("action", "publish")

    if action == "unpublish":
        form.is_published = False
        form.published_at = None
        form.save()
        return JsonResponse({"success": True, "is_published": False, "message": "Form unpublished."})

    form.is_published = True
    form.published_at = timezone.now()
    form.save()

    publish_link = request.build_absolute_uri(f"/f/{form.form_id}/")

    return JsonResponse({
        "success": True,
        "is_published": True,
        "publish_link": publish_link,
        "access_type": form.access_type,
        "message": "Form published."
    })


@transaction.atomic
def manage_access(request, form_id):

    if "user_id" not in request.session:
        return JsonResponse({"success": False, "message": "You must be logged in."}, status=401)

    try:
        form = Form.objects.get(form_id=form_id, owner__user_id=request.session["user_id"])
    except Form.DoesNotExist:
        return JsonResponse({"success": False, "message": "Form not found."}, status=404)

    # -------- GET: return current state to populate the modal --------
    if request.method == "GET":
        invites = list(form.invites.values("invite_id", "email","permission").order_by("email"))
        for i in invites:
            i["invite_id"] = str(i["invite_id"])

        return JsonResponse({
            "success": True,
            "access_type": form.access_type,
            "invites": invites
        })

    # -------- POST: mutate access settings --------
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

    action = request.POST.get("action")

    if action == "set_access_type":
        access_type = request.POST.get("access_type")

        if access_type not in ("anyone", "restricted"):
            return JsonResponse({"success": False, "message": "Invalid access type."}, status=400)

        form.access_type = access_type
        form.save()

        return JsonResponse({"success": True, "access_type": form.access_type})

    if action == "add_invite":
        email = (request.POST.get("email") or "").strip().lower()
        permission = request.POST.get("permission", "respond")

        if not email:
            return JsonResponse({"success": False, "message": "Email is required."}, status=400)
        if permission not in ("respond", "edit", "both"):
            permission = "respond"

        invite, created = FormInvite.objects.get_or_create(form=form, email=email, defaults={"permission": permission})
        if not created:
            invite.permission = permission
            invite.save()
        notify_invite_access(form, invite)

        return JsonResponse({
            "success": True,
            "invite": {"invite_id": str(invite.invite_id), "email": invite.email,"permission":invite.permission}
        })
    if action == "update_permission":
        invite_id = request.POST.get("invite_id")
        permission = request.POST.get("permission")

        if permission not in ("respond", "edit", "both"):
            return JsonResponse({"success": False, "message": "Invalid permission."}, status=400)
        try:
            invite = FormInvite.objects.get(form=form, invite_id=invite_id)
        except FormInvite.DoesNotExist:
            return JsonResponse({"success": False, "message": "Invite not found."}, status=404)

        invite.permission = permission
        invite.save()

        notify_invite_access(form, invite)

        return JsonResponse({"success": True})

    if action == "remove_invite":
        invite_id = request.POST.get("invite_id")

        FormInvite.objects.filter(form=form, invite_id=invite_id).delete()

        return JsonResponse({"success": True})
   

   


def view_form(request, form_id):

    try:
        form = Form.objects.prefetch_related("elements__options").get(form_id=form_id)
    except Form.DoesNotExist:
        return render(request, "form_not_found.html", status=404)

    status = form_access_status(request, form)

    if status == "not_found":
        return render(request, "form_not_found.html", status=404)
    if status == "denied":
        return render(request, "form_access_denied.html", status=403)

    return render(request, "public_form.html", {"form": form, "elements": form.elements.all()})


def validate_answer(element, post, files):
    """
    Returns (stored_text, uploaded_files, error_message).
    stored_text is "" when the question was left blank.
    """
    key = f"answer_{element.element_id}"
    qtype = element.question_type
    required = element.is_required
    required_msg = "This question is required."
    valid_options = [o.option_text for o in element.options.all()]

    def blank():
        return "", [], (required_msg if required else None)

    # ---- short answer / paragraph ----
    if qtype in ("short", "paragraph"):
        value = post.get(key, "").strip()
        limit = MAX_SHORT_LEN if qtype == "short" else MAX_LONG_LEN
        if not value:
            return blank()
        if len(value) > limit:
            return "", [], f"Please keep this answer under {limit} characters."
        return value, [], None

    # ---- multiple choice / dropdown ----
    if qtype in ("mcq", "dropdown"):
        value = post.get(key, "")
        if not value:
            return blank()
        if value not in valid_options:
            return "", [], "Please choose one of the listed options."
        return value, [], None

    # ---- checkboxes ----
    if qtype == "checkbox":
        values = post.getlist(key)
        if not values:
            return blank()
        if any(v not in valid_options for v in values):
            return "", [], "Please choose only from the listed options."
        return json.dumps(values), [], None

    # ---- linear scale ----
    if qtype == "linear_scale":
        raw = post.get(key, "").strip()
        if not raw:
            return blank()
        try:
            number = int(raw)
        except ValueError:
            return "", [], "Please pick a value on the scale."
        if number not in element.scale_range:
            return "", [], "That value is outside the scale."
        return str(number), [], None

    # ---- grids ----
    if qtype in ("mcq_grid", "checkbox_grid"):
        multi = qtype == "checkbox_grid"
        result = {}
        for i, row in enumerate(element.grid_row_list):
            picked = post.getlist(f"{key}__{i}")
            if not multi:
                picked = picked[:1]
            if any(p not in valid_options for p in picked):
                return "", [], "Please choose only from the listed columns."
            if picked:
                result[row] = picked if multi else picked[0]
            elif required:
                return "", [], f"Please answer every row (missing: {row})."
        return (json.dumps(result) if result else ""), [], None

    # ---- date / time ----
    if qtype in ("date", "time"):
        raw = post.get(key, "").strip()
        if not raw:
            return blank()
        try:
            parsed = parse_date(raw) if qtype == "date" else parse_time(raw)
        except ValueError:
            parsed = None
        if parsed is None:
            return "", [], f"Please enter a valid {qtype}."
        return (parsed.isoformat() if qtype == "date" else parsed.strftime("%H:%M")), [], None

    # ---- file upload ----
    if qtype == "file_upload":
        uploads = files.getlist(key)
        if not uploads:
            return blank()
        if len(uploads) > element.max_files:
            return "", [], f"You can upload at most {element.max_files} file(s)."
        for f in uploads:
            if f.size > MAX_UPLOAD_BYTES:
                return "", [], f"“{f.name}” is larger than 10 MB."
            if os.path.splitext(f.name)[1].lower() in BLOCKED_EXTENSIONS:
                return "", [], f"“{f.name}” is not an allowed file type."
        return "", uploads, None

    return "", [], None
@transaction.atomic
def submit_response(request, form_id):

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

    try:
        form = Form.objects.prefetch_related("elements__options").get(form_id=form_id)
    except Form.DoesNotExist:
        return JsonResponse({"success": False, "message": "This form doesn't exist."}, status=404)

    if not form.is_published:
        return JsonResponse({"success": False, "message": "This form isn't accepting responses."}, status=403)

    if form_access_status(request, form) != "ok":
        return JsonResponse({"success": False, "message": "You don't have access to this form."}, status=403)

    # ---- validate everything first; save nothing if anything fails ----
    errors = {}
    collected = []

    for element in form.elements.all():

        if element.element_type != "question":
            continue

        stored, uploads, error = validate_answer(element, request.POST, request.FILES)

        if error:
            errors[str(element.element_id)] = error
        elif stored or uploads:
            collected.append((element, stored, uploads))

    if errors:
        return JsonResponse({
            "success": False,
            "message": "Please fix the highlighted questions.",
            "errors": errors,
        }, status=400)

    if not collected:
        return JsonResponse({
            "success": False,
            "message": "Please answer at least one question before submitting.",
        }, status=400)

    # ---- save ----
    respondent = None
    if "user_id" in request.session:
        respondent = User.objects.filter(user_id=request.session["user_id"]).first()

    response = FormResponse.objects.create(form=form, respondent=respondent)

    for element, stored, uploads in collected:
        answer = Answer.objects.create(response=response, element=element, answer_text=stored)
        for upload in uploads:
            AnswerFile.objects.create(answer=answer, file=upload)
    notify_response_submitted(form, response)
    return JsonResponse({"success": True, "message": "Your response has been recorded."})
def build_summary(element, answers):

    qtype = element.question_type
    summary = {"element": element, "answered": len(answers), "answers": answers}

    if qtype in ("mcq", "dropdown", "checkbox"):

        counts = Counter()
        for a in answers:
            value = a.value
            counts.update(value if isinstance(value, list) else [value])

        summary["kind"] = "choice"
        summary["rows"] = [
            {
                "label": opt.option_text,
                "count": counts.get(opt.option_text, 0),
                "percent": round(100 * counts.get(opt.option_text, 0) / len(answers)) if answers else 0,
            }
            for opt in element.options.all()
        ]

    elif qtype == "linear_scale":

        counts = Counter()
        for a in answers:
            if a.answer_text.lstrip("-").isdigit():
                counts[int(a.answer_text)] += 1

        total = sum(counts.values())
        summary["kind"] = "choice"
        summary["rows"] = [
            {
                "label": n,
                "count": counts.get(n, 0),
                "percent": round(100 * counts.get(n, 0) / total) if total else 0,
            }
            for n in element.scale_range
        ]
        summary["average"] = round(sum(n * c for n, c in counts.items()) / total, 2) if total else None

    elif qtype in ("mcq_grid", "checkbox_grid"):

        columns = [o.option_text for o in element.options.all()]
        rows = element.grid_row_list
        counts = {row: Counter() for row in rows}

        for a in answers:
            for row, picked in a.grid_pairs:
                if row in counts:
                    counts[row].update(picked if isinstance(picked, list) else [picked])

        summary["kind"] = "grid"
        summary["columns"] = columns
        summary["table"] = [
            {"row": row, "cells": [counts[row].get(c, 0) for c in columns]}
            for row in rows
        ]

    elif qtype == "file_upload":
        summary["kind"] = "file"

    else:
        summary["kind"] = "text"

    return summary


def view_responses(request, form_id):

    if "user_id" not in request.session:
        return redirect("login")

    try:
        form = Form.objects.get(form_id=form_id, owner__user_id=request.session["user_id"])
    except Form.DoesNotExist:
        return HttpResponse("Form not found.", status=404)

    elements = list(form.elements.filter(element_type="question").prefetch_related("options"))
    responses = list(form.responses.select_related("respondent").order_by("-submitted_at"))

    answers = (
        Answer.objects.filter(response__form=form)
        .select_related("element")
        .prefetch_related("files")
    )

    by_response = defaultdict(dict)
    by_element = defaultdict(list)

    for a in answers:
        by_response[a.response_id][a.element_id] = a
        by_element[a.element_id].append(a)

    for r in responses:
        r.rows = [
            {"element": el, "answer": by_response[r.response_id].get(el.element_id)}
            for el in elements
        ]

    summaries = [build_summary(el, by_element[el.element_id]) for el in elements]

    return render(request, "responses.html", {
        "form": form,
        "responses": responses,
        "summaries": summaries,
        "response_count": len(responses),
    })

from django.core.mail import send_mail
from django.template.loader import render_to_string


def notify_response_submitted(form, response):

    if form.access_type != "restricted":
        return

    recipients = list(form.invites.values_list("email", flat=True))
    if not recipients:
        return

    subject = f"New response: {form.title}"

    body = render_to_string("emails/new_response.txt", {
        "form": form,
        "response": response,
    })

    try:
        send_mail(subject, body, None, recipients, fail_silently=False)
    except Exception as e:
        # Don't let a broken mail server break the actual submission.
        print(f"Email notification failed: {e}")


@require_POST
def delete_form(request, form_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    form = get_object_or_404(Form, form_id=form_id, owner_id=user_id)
    title = form.title
    form.delete()
    messages.success(request, f'Form "{title}" was deleted.')
    return redirect('forms_list')
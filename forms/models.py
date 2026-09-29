from django.db import models
import uuid

# Create your models here.
class User(models.Model):
    user_id= models.UUIDField(default=uuid.uuid1,primary_key=True,unique=True);
    name=models.CharField(max_length=200);
    password=models.CharField(max_length=200,blank=False);
    email=models.CharField(max_length=250,blank=False);
    departmentsList =[('F','Finance'),('HR','HR'),('Ink','Ink Store'),('It','IT'),('Maintain','Maintenance'),('Product','Production'),('Sales','Sales'),('Store','Store')]
    department=models.CharField(max_length=250,choices=departmentsList,default='IT')




class Form(models.Model):

    form_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="forms"
    )
    
    owner_name = models.CharField(
        max_length=200,
        blank=True
    )
    title = models.CharField(
        max_length=250,
        default="Untitled Form"
    )

    description = models.TextField(
        blank=True
    )

    is_published = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
    access_type = models.CharField(
        max_length=20,
        choices=[('anyone', 'Anyone with the link'), ('restricted', 'Restricted')],
        default='anyone'
    )

    def __str__(self):
        return self.title

class FormInvite(models.Model):
    invite_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='invites')
    email = models.EmailField()
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('form', 'email')

class Question(models.Model):

    QUESTION_TYPES = [
        ("short", "Short answer"),
        ("long", "Long answer"),
        ("multiple", "Multiple choice"),
        ("checkbox", "Checkboxes"),
        ("dropdown", "Dropdown"),
        ("date", "Date"),
        ("file", "File upload"),
    ]

    question_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    form = models.ForeignKey(
        Form,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    question_text = models.CharField(
        max_length=500
    )

    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default="short"
    )

    description = models.TextField(
        blank=True
    )

    is_required = models.BooleanField(
        default=False
    )

    order = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.question_text


class Option(models.Model):

    option_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options"
    )
    form = models.ForeignKey(
        Form,
        on_delete=models.CASCADE,
        related_name="options",
        null=True,
        blank=True
    )

    option_text = models.CharField(
        max_length=250
    )

    order = models.PositiveIntegerField(
        default=0
    )

    def __str__(self):
        return self.option_text


class Response(models.Model):

    response_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    form = models.ForeignKey(
        Form,
        on_delete=models.CASCADE,
        related_name="responses"
    )

    respondent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responses"
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Response to {self.form.title}"


class Answer(models.Model):

    answer_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    response = models.ForeignKey(
        Response,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    answer_text = models.TextField(
        blank=True
    )

    file = models.FileField(
        upload_to="form_answers/",
        blank=True,
        null=True
    )

    def __str__(self):
        return f"Answer to {self.question.question_text}"


class FormElement(models.Model):

    ELEMENT_TYPES = [
        ("question", "Question"),
        ("text", "Text/Description"),
        ("image", "Image"),
        ("sec", "Section"),
        
    ]

    QUESTION_TYPES = [
        ("short", "Short answer"),
        ("paragraph", "Paragraph"),
        ("mcq", "Multiple choice"),
        ("checkbox", "Checkboxes"),
        ("dropdown", "Dropdown"),
        ("file_upload", "File upload"),
        ("linear_scale", "Linear scale"),
        ("mcq_grid", "Multiple-choice grid"),
        ("checkbox_grid", "Checkbox grid"),
        ("date", "Date"),
        ("time", "Time"),
    ]

    element_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="elements")
    order = models.PositiveIntegerField()
    element_type = models.CharField(max_length=20, choices=ELEMENT_TYPES)

    # question-type fields
    question_text = models.CharField(max_length=1000, blank=True)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, blank=True)

    # text/sec-type fields
    title = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)

    # image-type field
    image = models.ImageField(upload_to="form_images/", null=True, blank=True)

    scale_min = models.PositiveIntegerField(null=True, blank=True)
    scale_max = models.PositiveIntegerField(null=True, blank=True)
    scale_min_label = models.CharField(max_length=100, blank=True)
    scale_max_label = models.CharField(max_length=100, blank=True)

    # grid config — rows stored newline-separated; columns reuse ElementOption
    grid_rows = models.TextField(blank=True)

    # file upload config
    max_files = models.PositiveIntegerField(default=1)

    is_required = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]


class ElementOption(models.Model):
    option_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    element = models.ForeignKey(FormElement, on_delete=models.CASCADE, related_name="options")
    option_text = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
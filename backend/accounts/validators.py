"""
Plain-function validators for the registration and login forms.

No Django Forms/ModelForm here on purpose — there's no Django Model
behind these fields (the record lives in MongoDB as a dict), so a
hand-rolled validator keeps the data flow obvious: request.POST in,
list of error strings + a clean dict out.
"""

import re
from datetime import datetime

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")  # Indian 10-digit mobile numbers
MIN_AGE_YEARS = 18


def validate_registration(data):
    """
    data: a dict-like object (e.g. request.POST) with the raw form fields.
    Returns (errors: list[str], cleaned: dict).
    """
    errors = []
    cleaned = {
        "full_name": data.get("full_name", "").strip(),
        "email": data.get("email", "").strip().lower(),
        "phone": data.get("phone", "").strip(),
        "gender": data.get("gender", "").strip().lower(),
        "dob": data.get("dob", "").strip(),
        "password": data.get("password", ""),
        "confirm_password": data.get("confirm_password", ""),
    }

    if len(cleaned["full_name"]) < 3:
        errors.append("Please enter your full name as it appears on your ID.")

    if not EMAIL_RE.match(cleaned["email"]):
        errors.append("Please enter a valid email address.")

    if not PHONE_RE.match(cleaned["phone"]):
        errors.append("Please enter a valid 10-digit mobile number.")

    if cleaned["gender"] not in ("male", "female", "other"):
        errors.append("Please select a gender.")

    if not cleaned["dob"]:
        errors.append("Please enter your date of birth.")
    else:
        try:
            birth_date = datetime.strptime(cleaned["dob"], "%Y-%m-%d")
            age_days = (datetime.now() - birth_date).days
            if age_days < MIN_AGE_YEARS * 365:
                errors.append("You must be at least 18 years old to create a profile.")
            if birth_date > datetime.now():
                errors.append("Date of birth cannot be in the future.")
        except ValueError:
            errors.append("Date of birth is not a valid date.")

    if len(cleaned["password"]) < 8:
        errors.append("Password must be at least 8 characters long.")

    if cleaned["password"] != cleaned["confirm_password"]:
        errors.append("Password and confirm password do not match.")

    if data.get("terms") != "on":
        errors.append("Please accept the Terms & Privacy Promise to continue.")

    return errors, cleaned


def validate_login(data):
    errors = []
    cleaned = {
        "identifier": data.get("identifier", "").strip().lower(),
        "password": data.get("password", ""),
    }
    if not cleaned["identifier"]:
        errors.append("Please enter your email or mobile number.")
    if not cleaned["password"]:
        errors.append("Please enter your password.")
    return errors, cleaned

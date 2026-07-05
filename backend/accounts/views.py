from datetime import datetime
import random

from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from bson import ObjectId


from .db import get_users_collection, get_db
from .validators import validate_login, validate_registration

# Helper to convert MongoDB _id to str
def serialize_user(user):
    if user and '_id' in user:
        user['id'] = str(user['_id'])
    return user

# --------------------- Auth ---------------------

def register_view(request):
    if request.session.get("user_id"):
        return redirect("dashboard")

    if request.method == "POST":
        errors, cleaned = validate_registration(request.POST)
        users = get_users_collection()

        if not errors:
            if users.find_one({"email": cleaned["email"]}):
                errors.append("An account with this email already exists.")
            if users.find_one({"phone": cleaned["phone"]}):
                errors.append("An account with this mobile number already exists.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "register.html", {"form_data": request.POST})

        # Calculate age from DOB
        birth_date = datetime.strptime(cleaned["dob"], "%Y-%m-%d")
        age = (datetime.now() - birth_date).days // 365

        user_doc = {
            "full_name": cleaned["full_name"],
            "email": cleaned["email"],
            "phone": cleaned["phone"],
            "gender": cleaned["gender"],
            "dob": cleaned["dob"],
            "age": age,
            "password": make_password(cleaned["password"]),
            "created_at": datetime.utcnow(),
            # Additional profile fields – user can fill later
            "profession": "",
            "city": "",
            "education": "",
            "height": "",
            "religion": "",
            "mother_tongue": "",
            "bio": "",
            "verified": False,
        }
        result = users.insert_one(user_doc)

        request.session["user_id"] = str(result.inserted_id)
        request.session["full_name"] = cleaned["full_name"]
        messages.success(request, f"Welcome, {cleaned['full_name'].split()[0]}!")
        return redirect("dashboard")

    return render(request, "register.html")


def login_view(request):
    if request.session.get("user_id"):
        return redirect("dashboard")

    if request.method == "POST":
        errors, cleaned = validate_login(request.POST)
        if not errors:
            users = get_users_collection()
            user = users.find_one(
                {"$or": [{"email": cleaned["identifier"]}, {"phone": cleaned["identifier"]}]}
            )
            if user and check_password(cleaned["password"], user["password"]):
                request.session["user_id"] = str(user["_id"])
                request.session["full_name"] = user["full_name"]
                return redirect("dashboard")
            errors.append("Email/mobile or password is incorrect.")

        for err in errors:
            messages.error(request, err)
        return render(request, "login.html", {"form_data": request.POST})

    return render(request, "login.html")


def logout_view(request):
    request.session.flush()
    messages.success(request, "You've been signed out.")
    return redirect("login")


# --------------------- Dashboard & Profiles ---------------------

def dashboard_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please sign in first.")
        return redirect("login")

    users = get_users_collection()
    current_user = users.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        request.session.flush()
        return redirect("login")

    opposite_gender = "female" if current_user["gender"] == "male" else "male"

    # Build query for profiles
    query = {"gender": opposite_gender}
    # Exclude own user (just in case)
    query["_id"] = {"$ne": ObjectId(user_id)}

    # Filters from GET
    search = request.GET.get("search", "").strip()
    age_filter = request.GET.get("age", "")
    city_filter = request.GET.get("city", "")

    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"profession": {"$regex": search, "$options": "i"}},
        ]
    if age_filter:
        try:
            min_a, max_a = map(int, age_filter.split("-"))
            query["age"] = {"$gte": min_a, "$lte": max_a}
        except:
            pass
    if city_filter:
        query["city"] = {"$regex": f"^{city_filter}$", "$options": "i"}

    profiles_cursor = users.find(query)
    profiles = list(profiles_cursor)

    # Get interests collection
    db = get_db()
    interests_col = db["interests"]

    # Annotate each profile
    for p in profiles:
        p["id"] = str(p["_id"])
        # Compatibility score (deterministic)
        score = 75 + (sum(ord(c) for c in p["full_name"]) % 24)
        p["compatibility"] = score
        # Check if current user already sent interest
        interest = interests_col.find_one({
            "from_user_id": ObjectId(user_id),
            "to_user_id": p["_id"]
        })
        p["interested"] = bool(interest)

    # List of cities for filter
    cities = users.distinct("city", {"gender": opposite_gender})
    cities = [c for c in cities if c]

    context = {
        "full_name": current_user["full_name"],
        "profiles": profiles,
        "cities": cities,
        "search": search,
        "age": age_filter,
        "city": city_filter,
        "user_gender": current_user["gender"],
    }
    return render(request, "dashboard.html", context)


def profile_detail(request, profile_id):
    """AJAX endpoint for profile modal."""
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    users = get_users_collection()
    profile = users.find_one({"_id": ObjectId(profile_id)})
    if not profile:
        return JsonResponse({"error": "Profile not found"}, status=404)

    # Security: only show opposite gender profiles
    current_user = users.find_one({"_id": ObjectId(user_id)})
    if profile["gender"] == current_user["gender"]:
        return JsonResponse({"error": "Not allowed"}, status=403)

    # Compute compatibility
    score = 75 + (sum(ord(c) for c in profile["full_name"]) % 24)

    # Check interest
    db = get_db()
    interests = db["interests"]
    interested = bool(interests.find_one({
        "from_user_id": ObjectId(user_id),
        "to_user_id": ObjectId(profile_id)
    }))

    data = {
        "id": str(profile["_id"]),
        "full_name": profile["full_name"],
        "age": profile.get("age", 0),
        "profession": profile.get("profession", ""),
        "city": profile.get("city", ""),
        "education": profile.get("education", ""),
        "height": profile.get("height", ""),
        "religion": profile.get("religion", ""),
        "mother_tongue": profile.get("mother_tongue", ""),
        "bio": profile.get("bio", ""),
        "verified": profile.get("verified", False),
        "compatibility": score,
        "interested": interested,
    }
    return JsonResponse(data)


@require_POST
def toggle_interest(request, profile_id):
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    users = get_users_collection()
    profile = users.find_one({"_id": ObjectId(profile_id)})
    if not profile:
        return JsonResponse({"error": "Profile not found"}, status=404)

    current_user = users.find_one({"_id": ObjectId(user_id)})
    if profile["gender"] == current_user["gender"]:
        return JsonResponse({"error": "Cannot send interest to same gender"}, status=403)

    db = get_db()
    interests = db["interests"]

    existing = interests.find_one({
        "from_user_id": ObjectId(user_id),
        "to_user_id": ObjectId(profile_id)
    })

    if existing:
        interests.delete_one({"_id": existing["_id"]})
        interested = False
    else:
        interests.insert_one({
            "from_user_id": ObjectId(user_id),
            "to_user_id": ObjectId(profile_id),
            "created_at": datetime.utcnow()
        })
        interested = True

    return JsonResponse({"interested": interested})


# --------------------- Profile Edit (optional) ---------------------

def settings_view(request):
    """Simple settings page placeholder."""
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please sign in first.")
        return redirect("login")

    users = get_users_collection()
    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        request.session.flush()
        return redirect("login")

    return render(request, "settings.html", {"user": user})


def edit_profile_view(request):
    """Edit profile page."""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    users = get_users_collection()
    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        request.session.flush()
        return redirect("login")

    if request.method == "POST":
        update_data = {
            "full_name": request.POST.get("full_name", user["full_name"]),
            "profession": request.POST.get("profession", ""),
            "city": request.POST.get("city", ""),
            "education": request.POST.get("education", ""),
            "height": request.POST.get("height", ""),
            "religion": request.POST.get("religion", ""),
            "mother_tongue": request.POST.get("mother_tongue", ""),
            "bio": request.POST.get("bio", ""),
        }
        dob = request.POST.get("dob")
        if dob:
            birth = datetime.strptime(dob, "%Y-%m-%d")
            update_data["age"] = (datetime.now() - birth).days // 365
            update_data["dob"] = dob

        users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        messages.success(request, "Profile updated successfully!")
        return redirect("dashboard")

    context = {"user": user}
    return render(request, "edit_profile.html", context)


def debug_session_view(request):
    """Debug helper to inspect session state."""
    keys = list(request.session.keys())
    return JsonResponse({
        "keys": keys,
        "has_user_id": bool(request.session.get("user_id")),
        "user_id": request.session.get("user_id"),
        "full_name": request.session.get("full_name"),
    })
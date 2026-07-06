from datetime import datetime
import random
import base64



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
            "profile_pic_is_profile_pic": False,
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
        "profile_pic_is_profile_pic": bool(profile.get("profile_pic_is_profile_pic")),
        "profile_pic": (
            bool(profile.get("profile_pic_is_profile_pic")) and profile.get("profile_pic_content_type") and profile.get("profile_pic")
        ) and ("data:" + profile.get("profile_pic_content_type") + ";base64," + profile.get("profile_pic")) or None,
        "profile_pic_filename": profile.get("profile_pic_filename", ""),
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
        # If the sender withdraws interest, also mark related unread notifications as read
        # (prevents stale "sent you a request" items).
        db = get_db()
        notif_col = db["notifications"]
        notif_col.update_many({
            "to_user_id": ObjectId(profile_id),
            "from_user_id": ObjectId(user_id),
            "type": "interest_request",
            "status": "unread",
        }, {"$set": {"status": "read"}})
        interested = False
    else:
        interests.insert_one({
            "from_user_id": ObjectId(user_id),
            "to_user_id": ObjectId(profile_id),
            "created_at": datetime.utcnow()
        })

        # Create notification for the recipient so they can accept/decline.
        db = get_db()
        notif_col = db["notifications"]
        notif_col.insert_one({
            "to_user_id": ObjectId(profile_id),
            "from_user_id": ObjectId(user_id),
            "type": "interest_request",
            "status": "unread",
            "created_at": datetime.utcnow(),
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
            "full_name": request.POST.get("full_name", user.get("full_name", "")),
            "profession": request.POST.get("profession", ""),
            "city": request.POST.get("city", ""),
            "education": request.POST.get("education", ""),
            "height": request.POST.get("height", ""),
            "religion": request.POST.get("religion", ""),
            "mother_tongue": request.POST.get("mother_tongue", ""),
            "bio": request.POST.get("bio", ""),
        }

        # Optional DOB update
        dob = request.POST.get("dob")
        if dob:
            birth = datetime.strptime(dob, "%Y-%m-%d")
            update_data["age"] = (datetime.now() - birth).days // 365
            update_data["dob"] = dob

        # Optional profile picture upload (stored in MongoDB as base64)
        pic = request.FILES.get("profile_pic")
        if pic:
            # Basic validation
            content_type = getattr(pic, "content_type", "") or ""
            if not content_type.startswith("image/"):
                messages.error(request, "Invalid file type. Please upload an image.")
                return render(request, "edit_profile.html", {"user": user})

            # keep it safe: cap size (e.g. 2MB)
            if pic.size and pic.size > 2 * 1024 * 1024:
                messages.error(request, "Image is too large. Max size is 2MB.")
                return render(request, "edit_profile.html", {"user": user})

            raw = pic.read()

            # Prefer provided content-type (we only accept image/* above)
            stored_content_type = content_type if content_type.startswith("image/") else "image/jpeg"

            update_data["profile_pic"] = base64.b64encode(raw).decode("utf-8")
            update_data["profile_pic_content_type"] = stored_content_type
            update_data["profile_pic_filename"] = getattr(pic, "name", "")
            update_data["profile_pic_uploaded_at"] = datetime.utcnow()

            update_data["profile_pic_is_profile_pic"] = True
        else:
            # Keep the boolean accurate even when user doesn't upload a new image.
            # If existing doc already has pic content, keep True; otherwise False.
            has_existing_pic = bool(user.get("profile_pic")) and bool(user.get("profile_pic_content_type"))
            update_data["profile_pic_is_profile_pic"] = has_existing_pic

        users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        messages.success(request, "Profile updated successfully!")
        return redirect("dashboard")

    context = {"user": user}
    return render(request, "edit_profile.html", context)



def _require_user_id(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return user_id


def _conversation_key(a_id, b_id):
    """Create a deterministic key for a 2-person conversation."""
    a = str(a_id)
    b = str(b_id)
    return "__".join(sorted([a, b]))



def notifications_list(request):
    """Return unread notifications for current user."""
    user_id = _require_user_id(request)
    if not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    db = get_db()
    notif_col = db["notifications"]

    notifs = list(
        notif_col.find(
            {"to_user_id": ObjectId(user_id), "status": "unread"}
        ).sort("created_at", -1).limit(50)
    )

    # Marking read is done on accept/decline; but the list endpoint can mark as read.
    # We'll keep it non-destructive for better UX: client marks read implicitly by refreshing.

    payload = []
    users = get_users_collection()
    for n in notifs:
        from_uid = n["from_user_id"]
        from_user = users.find_one({"_id": from_uid})
        payload.append({
            "from_user_id": str(from_uid),
            "from_full_name": from_user.get("full_name", "") if from_user else "",
            "type": n.get("type"),
            "created_at": n.get("created_at"),
            "profile_id": str(from_uid),
        })

    return JsonResponse({"notifications": payload})


@require_POST
def interest_accept(request, profile_id):
    """Accept an incoming interest request and enable chat."""
    user_id = _require_user_id(request)
    if not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    users = get_users_collection()
    current_user = users.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    incoming_from = ObjectId(profile_id)
    if incoming_from == ObjectId(user_id):
        return JsonResponse({"error": "Invalid user"}, status=400)

    db = get_db()
    interests = db["interests"]
    connections = db["connections"]
    notif_col = db["notifications"]

    existing_interest = interests.find_one({
        "from_user_id": incoming_from,
        "to_user_id": ObjectId(user_id)
    })
    if not existing_interest:
        return JsonResponse({"error": "No incoming request"}, status=404)

    # Create connection (idempotent)
    connections.create_index([("user1_id", 1), ("user2_id", 1)], unique=True)
    u1 = str(incoming_from)
    u2 = str(ObjectId(user_id))
    key = _conversation_key(u1, u2)

    # Normalize user1/user2 for unique constraint
    if u1 < u2:
        user1 = incoming_from
        user2 = ObjectId(user_id)
    else:
        user1 = ObjectId(user_id)
        user2 = incoming_from

    try:
        connections.insert_one({
            "user1_id": user1,
            "user2_id": user2,
            "conversation_key": key,
            "created_at": datetime.utcnow(),
        })
    except Exception:
        # If already exists, ignore.
        pass

    # Remove interest request
    interests.delete_one({"_id": existing_interest["_id"]})

    # Create notification for the other user
    # (mark any existing unread interest_request notifications as read)
    notif_col.update_many({
        "to_user_id": incoming_from,
        "from_user_id": ObjectId(user_id),
        "type": "interest_request",
        "status": "unread",
    }, {"$set": {"status": "read"}})

    notif_col.insert_one({
        "to_user_id": incoming_from,
        "from_user_id": ObjectId(user_id),
        "type": "interest_accepted",
        "status": "unread",
        "created_at": datetime.utcnow(),
    })

    # Mark related incoming notification (for current user) as read
    notif_col.update_many({
        "to_user_id": ObjectId(user_id),
        "from_user_id": incoming_from,
        "type": "interest_request",
        "status": "unread",
    }, {"$set": {"status": "read"}})

    return JsonResponse({"ok": True})


@require_POST
def interest_decline(request, profile_id):
    """Decline an incoming interest request."""
    user_id = _require_user_id(request)
    if not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    incoming_from = ObjectId(profile_id)
    db = get_db()
    interests = db["interests"]
    notif_col = db["notifications"]

    existing_interest = interests.find_one({
        "from_user_id": incoming_from,
        "to_user_id": ObjectId(user_id)
    })
    if not existing_interest:
        return JsonResponse({"error": "No incoming request"}, status=404)

    interests.delete_one({"_id": existing_interest["_id"]})

    notif_col.update_many({
        "to_user_id": ObjectId(user_id),
        "from_user_id": incoming_from,
        "type": "interest_request",
        "status": "unread",
    }, {"$set": {"status": "read"}})

    return JsonResponse({"ok": True})


def conversations_list(request):
    """List conversations current user can chat in."""
    user_id = _require_user_id(request)
    if not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    uid = ObjectId(user_id)
    db = get_db()
    connections = db["connections"]
    users = get_users_collection()

    conns = list(connections.find({
        "$or": [
            {"user1_id": uid},
            {"user2_id": uid},
        ]
    }).sort("created_at", -1).limit(50))

    out = []
    for c in conns:
        other_id = c["user2_id"] if c.get("user1_id") == uid else c.get("user1_id")
        other = users.find_one({"_id": other_id})
        out.append({
            "partner_id": str(other_id),
            "partner_full_name": other.get("full_name", "") if other else "",
        })

    return JsonResponse({"conversations": out})


def messages_list(request, partner_id):
    """Fetch messages in conversation with partner."""
    user_id = _require_user_id(request)
    if not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    me = ObjectId(user_id)
    partner = ObjectId(partner_id)

    db = get_db()
    messages_col = db["messages"]

    key = _conversation_key(me, partner)

    msgs = list(messages_col.find({"conversation_key": key}).sort("created_at", 1).limit(200))
    payload = []
    for m in msgs:
        payload.append({
            "sender_id": str(m.get("sender_id")),
            "receiver_id": str(m.get("receiver_id")),
            "text": m.get("text", ""),
            "created_at": m.get("created_at"),
        })

    return JsonResponse({"messages": payload})


@require_POST
def messages_send(request, partner_id):
    """Send a message to partner."""
    user_id = _require_user_id(request)
    if not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    me = ObjectId(user_id)
    partner = ObjectId(partner_id)

    try:
        body = request.body.decode("utf-8")
    except Exception:
        body = "{}"

    # Accept either json payload or empty body
    text = ""
    try:
        import json
        data = json.loads(body) if body else {}
        text = (data.get("text") or "").strip()
    except Exception:
        text = (request.POST.get("text") or "").strip()

    if not text:
        return JsonResponse({"error": "Text required"}, status=400)

    db = get_db()
    messages_col = db["messages"]
    connections = db["connections"]

    # Ensure they are connected
    conns = connections.find_one({
        "$or": [
            {
                "$and": [
                    {"user1_id": me},
                    {"user2_id": partner},
                ]
            },
            {
                "$and": [
                    {"user1_id": partner},
                    {"user2_id": me},
                ]
            },
        ]
    })
    if not conns:
        return JsonResponse({"error": "No chat connection"}, status=403)

    key = _conversation_key(me, partner)

    messages_col.insert_one({
        "conversation_key": key,
        "sender_id": me,
        "receiver_id": partner,
        "text": text,
        "created_at": datetime.utcnow(),
    })

    return JsonResponse({"ok": True})


def debug_session_view(request):
    """Debug helper to inspect session state."""
    keys = list(request.session.keys())
    return JsonResponse({
        "keys": keys,
        "has_user_id": bool(request.session.get("user_id")),
        "user_id": request.session.get("user_id"),
        "full_name": request.session.get("full_name"),
    })

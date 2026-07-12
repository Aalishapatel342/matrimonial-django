from datetime import datetime

from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect, render

from bson import ObjectId
import pymongo


from .db import get_users_collection
from .validators import validate_login, validate_registration



def register_view(request):
    if request.session.get("user_id"):
        return redirect("dashboard")

    if request.method == "POST":
        errors, cleaned = validate_registration(request.POST)

        if not errors:
            # Only hit MongoDB once the basic field validation has
            # already passed — no point querying the database for a
            # submission that's invalid anyway.
            users = get_users_collection()
            if users.find_one({"email": cleaned["email"]}):
                errors.append("An account with this email already exists.")
            if users.find_one({"phone": cleaned["phone"]}):
                errors.append("An account with this mobile number already exists.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "register.html", {"form_data": request.POST})

        user_doc = {
            "full_name": cleaned["full_name"],
            "email": cleaned["email"],
            "phone": cleaned["phone"],
            "gender": cleaned["gender"],
            "dob": cleaned["dob"],
            "password": make_password(cleaned["password"]),
            "created_at": datetime.utcnow(),
        }
        result = users.insert_one(user_doc)

        request.session["user_id"] = str(result.inserted_id)
        request.session["full_name"] = cleaned["full_name"]
        messages.success(
            request, f"Welcome to Vivah, {cleaned['full_name'].split()[0]}! Your profile is live."
        )
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
            errors.append("That email/mobile number and password don't match our records.")

        for err in errors:
            messages.error(request, err)
        return render(request, "login.html", {"form_data": request.POST})

    return render(request, "login.html")


def logout_view(request):
    request.session.flush()
    # Prevent "Please sign in to continue" errors from protected pages
    # appearing again on the login page after logout.
    storage = list(messages.get_messages(request))

    messages.success(request, "You've been signed out. See you again soon.")
    return redirect("/login/")

def _get_blocked_other_ids(db, user_oid):
    """Return ObjectIds of users blocked by `user_oid`.

    Also excludes `None` and converts to proper ObjectId if needed.


    We store mutual documents in collection `blocks`:
      { user_id: A, blocked_id: B }
      { user_id: B, blocked_id: A }
    So for filtering, we only need rows where user_id == current user.
    """
    blocks = db.get_collection("blocks")
    rows = blocks.find({"user_id": user_oid}, {"blocked_id": 1}).limit(500)
    return [r.get("blocked_id") for r in rows if r.get("blocked_id")]


def dashboard_view(request):
    """Render dashboard.

    The template is mostly driven by JS + a few server-side context values
    (gender + initial profiles list + filters).

    Frontend expects:
      - user_gender
      - profiles (list of profile dicts)
      - cities, search, age, city
    """
    if not request.session.get("user_id"):
        messages.error(request, "Please sign in to continue.")
        return redirect("login")

    from .db import get_users_collection

    full_name = request.session.get("full_name") or "Guest"
    user_id = request.session.get("user_id")

    users = get_users_collection()
    me = users.find_one({"_id": ObjectId(user_id)})

    # user_gender is used in template conditional to show opposite profiles
    user_gender = (me.get("gender") if me else None) or request.session.get("gender") or ""

    # Simplified matchmaking: show users whose gender is opposite to current
    # user_gender.
    if user_gender.lower() == "male":
        target_gender = "female"
    elif user_gender.lower() == "female":
        target_gender = "male"
    else:
        target_gender = None

    search = request.GET.get("search", "")
    age = request.GET.get("age", "")
    city = request.GET.get("city", "")

    query = {}
    if target_gender:
        query["gender"] = target_gender
    if search:
        query["full_name"] = {"$regex": search, "$options": "i"}
    if city:
        query["city"] = city

    # Basic age filter handling (template uses buckets)
    if age:
        if age == "18-25":
            query["age"] = {"$gte": 18, "$lte": 25}
        elif age == "26-30":
            query["age"] = {"$gte": 26, "$lte": 30}
        elif age == "31-35":
            query["age"] = {"$gte": 31, "$lte": 35}
        elif age == "36-99":
            query["age"] = {"$gte": 36}

    # Exclude blocked users from dashboard results
    blocked_ids = _get_blocked_other_ids(users.database, me.get("_id")) if me else []
    if blocked_ids:
        query["_id"] = {"$nin": blocked_ids}

    profiles_cursor = users.find(query)


    # Render cards. Interest state is handled later by JS toggle endpoint,
    # so we just provide defaults here.
    profiles = []
    for p in profiles_cursor.limit(50):
        profiles.append(
            {
                "id": str(p.get("_id")),
                "full_name": p.get("full_name", ""),
                "age": p.get("age", 0),
                "profession": p.get("profession", ""),
                "city": p.get("city", ""),
                "education": p.get("education", ""),
                "height": p.get("height", ""),
                "religion": p.get("religion", ""),
                "mother_tongue": p.get("mother_tongue", ""),
                "bio": p.get("bio", ""),
                "verified": bool(p.get("verified", False)),
                "compatibility": p.get("compatibility")
                if p.get("compatibility") is not None
                else 70,
                "interested": False,
            }
        )

    cities = sorted({p.get("city", "") for p in users.find(query, {"city": 1}) if p.get("city")})

    return render(
        request,
        "dashboard.html",
        {
            "full_name": full_name,
            "user_gender": user_gender,
            "profiles": profiles,
            "search": search,
            "age": age,
            "city": city,
            "cities": cities,
        },
    )




def settings_view(request):
    if not request.session.get("user_id"):
        messages.error(request, "Please sign in to continue.")
        return redirect("login")
    return render(request, "settings.html", {"full_name": request.session.get("full_name")})


def edit_profile_view(request):
    """Render/edit the current user profile.

    This app stores user/account + profile fields in MongoDB, but the
    repository currently lacks a full profile-edit implementation.

    The goal of this view is to provide a valid URL name for templates
    ("edit_profile") and prevent NoReverseMatch crashes.
    """
    if not request.session.get("user_id"):
        messages.error(request, "Please sign in to continue.")
        return redirect("login")

    # Minimal context so the template can render even if profile fields
    # aren't implemented in Mongo yet.
    user = {
        "full_name": request.session.get("full_name", ""),
        "email": request.session.get("email", ""),
        "gender": request.session.get("gender", ""),
        "dob": request.session.get("dob", ""),
        "profession": request.session.get("profession", ""),
        "city": request.session.get("city", ""),
        "education": request.session.get("education", ""),
        "height": request.session.get("height", ""),
        "annual_salary": request.session.get("annual_salary", ""),
        "religion": request.session.get("religion", ""),
        "mother_tongue": request.session.get("mother_tongue", ""),
        "bio": request.session.get("bio", ""),
        "age": request.session.get("age", ""),
    }

    if request.method == "POST":
        users = get_users_collection()
        user_oid = _get_request_user_object_id(request)
        if not user_oid:
            messages.error(request, "Session expired. Please sign in again.")
            return redirect("login")

        payload = {
            "full_name": (request.POST.get("full_name") or "").strip(),
            "dob": request.POST.get("dob") or None,
            "profession": (request.POST.get("profession") or "").strip(),
            "city": (request.POST.get("city") or "").strip(),
            "education": (request.POST.get("education") or "").strip(),
            "height": (request.POST.get("height") or "").strip(),
            "religion": (request.POST.get("religion") or "").strip(),
            "mother_tongue": (request.POST.get("mother_tongue") or "").strip(),
            "bio": (request.POST.get("bio") or "").strip(),
        }

        # Optional salary field (annual_salary)
        raw = (request.POST.get("annual_salary") or "").strip()
        if raw != "":
            try:
                payload["annual_salary"] = int(raw)
            except ValueError:
                pass

        # Handle profile picture (stored in MongoDB as base64)
        f = request.FILES.get("profile_pic")
        if f:
            import base64
            payload["profile_pic"] = base64.b64encode(f.read()).decode("utf-8")
            payload["profile_pic_content_type"] = getattr(f, "content_type", "application/octet-stream")
            payload["profile_pic_is_profile_pic"] = True

        users.update_one({"_id": user_oid}, {"$set": payload}, upsert=False)

        # Refresh session values used in templates
        request.session["full_name"] = payload.get("full_name") or request.session.get("full_name")
        for key in ["dob","profession","city","education","height","religion","mother_tongue","bio","annual_salary"]:
            if key in payload:
                request.session[key] = payload[key]

        messages.success(request, "Profile update saved.")
        return redirect("dashboard")

    return render(request, "edit_profile.html", {"user": user})


def _get_request_user_id(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return str(user_id)


def _get_request_user_object_id(request):
    user_id = _get_request_user_id(request)
    if not user_id:
        return None
    return ObjectId(user_id)


def notifications_view(request):
    """Return received requests (for navbar notification panel)."""
    from django.http import JsonResponse
    if request.method != "GET":
        return JsonResponse({"notifications": []})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"notifications": []})

    users = get_users_collection()
    notifications = []

    # Mongo schema (expected): interests collection holds pending requests.
    db = users.database
    interests = db.get_collection("interests")

    pending = interests.find({"to_user_id": user_oid, "status": "pending"}).limit(50)
    for item in pending:
        from_id = item.get("from_user_id")
        profile_id = item.get("profile_id") or from_id
        from_user = users.find_one({"_id": from_id}) or {}
        notifications.append(
            {
                "profile_id": str(profile_id),
                "from_user_id": str(from_id) if from_id else "",
                "from_full_name": from_user.get("full_name") or "User",
            }
        )

    return JsonResponse({"notifications": notifications})


def interest_toggle_view(request, profile_id):
    """Send interest if not exists; withdraw if exists.

    The interests collection has a unique index on:
      { from_user_id: 1, to_user_id: 1 }

    This endpoint must be idempotent and safe under concurrent requests.
    """
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"interested": False})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"interested": False})

    # Block enforcement (mutual)
    try:
        to_oid_tmp = ObjectId(profile_id)
    except Exception:
        to_oid_tmp = None

    users = get_users_collection()
    db = users.database
    if to_oid_tmp and _is_blocked_mutual(db, user_oid, to_oid_tmp):
        return JsonResponse({"interested": False, "blocked": True})


    from_id = _get_request_user_object_id(request)
    if not from_id:
        return JsonResponse({"interested": False})

    try:
        to_oid = ObjectId(profile_id)
    except Exception:
        return JsonResponse({"interested": False})

    users = get_users_collection()
    db = users.database
    interests = db.get_collection("interests")

    unique_filter = {"from_user_id": from_id, "to_user_id": to_oid}

    try:
        # If already pending, toggle off (decline)
        existing = interests.find_one(
            {
                **unique_filter,
                "status": "pending",
            }
        )
        if existing:
            interests.update_one(
                {"_id": existing["_id"]},
                {"$set": {"status": "declined", "updated_at": datetime.utcnow()}},
            )
            return JsonResponse({"interested": False})

        # Otherwise set/create pending using the unique index filter only.
        interests.update_one(
            unique_filter,
            {
                "$set": {"status": "pending", "updated_at": datetime.utcnow()},
                "$setOnInsert": {"from_user_id": from_id, "to_user_id": to_oid},
            },
            upsert=True,
        )

        return JsonResponse({"interested": True})

    except pymongo.errors.DuplicateKeyError:
        # Race: someone inserted the same unique pair just now.
        # Convert to the desired state with a plain update.
        interests.update_one(
            unique_filter,
            {"$set": {"status": "pending", "updated_at": datetime.utcnow()}},
            upsert=False,
        )
        return JsonResponse({"interested": True})



def interest_accept_view(request, profile_id):
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"ok": False})

    to_oid = _get_request_user_object_id(request)
    if not to_oid:
        return JsonResponse({"ok": False})

    from_oid = ObjectId(profile_id)

    users = get_users_collection()
    db = users.database
    interests = db.get_collection("interests")
    pinned = db.get_collection("pinned")
    chats = db.get_collection("conversations")

    # Find matching pending request (from->to)
    pending = interests.find_one(
        {"from_user_id": from_oid, "to_user_id": to_oid, "status": "pending"}
    )

    if not pending:
        return JsonResponse({"ok": False})

    interests.update_one({"_id": pending["_id"]}, {"$set": {"status": "accepted", "updated_at": datetime.utcnow()}})

    # Create pinned connection
    pinned.update_one(
        {"user_id": to_oid, "partner_id": from_oid},
        {
            "$setOnInsert": {
                "user_id": to_oid,
                "partner_id": from_oid,
                "created_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )
    pinned.update_one(
        {"user_id": from_oid, "partner_id": to_oid},
        {
            "$setOnInsert": {
                "user_id": from_oid,
                "partner_id": to_oid,
                "created_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )

    # Create conversation if not exists
    chats.update_one(
        {"user_id": to_oid, "partner_id": from_oid},
        {"$setOnInsert": {"user_id": to_oid, "partner_id": from_oid, "created_at": datetime.utcnow()}},
        upsert=True,
    )
    chats.update_one(
        {"user_id": from_oid, "partner_id": to_oid},
        {"$setOnInsert": {"user_id": from_oid, "partner_id": to_oid, "created_at": datetime.utcnow()}},
        upsert=True,
    )

    return JsonResponse({"ok": True})


def interest_decline_view(request, profile_id):
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"ok": False})

    to_oid = _get_request_user_object_id(request)
    if not to_oid:
        return JsonResponse({"ok": False})

    from_oid = ObjectId(profile_id)

    users = get_users_collection()
    db = users.database
    interests = db.get_collection("interests")

    interests.update_one(
        {"from_user_id": from_oid, "to_user_id": to_oid, "status": "pending"},
        {"$set": {"status": "declined", "updated_at": datetime.utcnow()}},
    )

    return JsonResponse({"ok": True})


def pinned_view(request):
    from django.http import JsonResponse

    if request.method != "GET":
        return JsonResponse({"pinned_profiles": []})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"pinned_profiles": []})

    users = get_users_collection()
    db = users.database
    pinned = db.get_collection("pinned")

    pinned_docs = pinned.find({"user_id": user_oid}).limit(50)
    out = []
    for p in pinned_docs:
        partner_oid = p.get("partner_id")
        partner = users.find_one({"_id": partner_oid}) or {}
        out.append(
            {
                "id": str(partner_oid),
                "full_name": partner.get("full_name", ""),
                "age": partner.get("age", ""),
                "profession": partner.get("profession", ""),
                "city": partner.get("city", ""),
                "education": partner.get("education", ""),
                "height": partner.get("height", ""),
                "religion": partner.get("religion", ""),
                "mother_tongue": partner.get("mother_tongue", ""),
                "bio": partner.get("bio", ""),
                "verified": bool(partner.get("verified", False)),
                "profile_pic_is_profile_pic": bool(partner.get("profile_pic_is_profile_pic", False)),
                "profile_pic": partner.get("profile_pic"),
                "profile_pic_content_type": partner.get("profile_pic_content_type"),
                "compatibility": partner.get("compatibility") or 70,
                "profile_pic_is_profile_pic": bool(partner.get("profile_pic_is_profile_pic", False)),
            }
        )

    return JsonResponse({"pinned_profiles": out})


def connection_status_view(request, profile_id):
    """Return connection state for the logged-in user relative to `profile_id`.

    Response:
      - {state: "connected"}
      - {state: "pending"}      (has accepted interest from this user to that user? UI treats as Interest Sent)
      - {state: "none"}

    Frontend uses this to update the main-grid button to "Connected" immediately after accept.
    """
    from django.http import JsonResponse

    if request.method != "GET":
        return JsonResponse({"state": "none"})

    from_oid = _get_request_user_object_id(request)
    if not from_oid:
        return JsonResponse({"state": "none"})

    try:
        to_oid = ObjectId(profile_id)
    except Exception:
        return JsonResponse({"state": "none"})

    users = get_users_collection()
    db = users.database

    pinned = db.get_collection("pinned")
    interests = db.get_collection("interests")

    # Connected if pinned row exists for either direction.
    is_connected = bool(
        pinned.find_one({"user_id": from_oid, "partner_id": to_oid})
        or pinned.find_one({"user_id": to_oid, "partner_id": from_oid})
    )
    if is_connected:
        return JsonResponse({"state": "connected"})

    # Pending if there is a pending interest record from me -> target
    is_pending = bool(
        interests.find_one({
            "from_user_id": from_oid,
            "to_user_id": to_oid,
            "status": "pending",
        })
    )
    if is_pending:
        return JsonResponse({"state": "pending"})

    return JsonResponse({"state": "none"})


def profile_detail_view(request, profile_id):
    from django.http import JsonResponse

    if request.method != "GET":
        return JsonResponse({"ok": False})

    users = get_users_collection()
    user = users.find_one({"_id": ObjectId(profile_id)}) or {}

    interested = False
    # Determine if current user has pending interest to this profile
    to_user_oid = ObjectId(profile_id)
    from_oid = _get_request_user_object_id(request)
    if from_oid:
        db = users.database
        interests = db.get_collection("interests")
        interested = bool(
            interests.find_one(
                {"from_user_id": from_oid, "to_user_id": to_user_oid, "status": "pending"}
            )
        )

    return JsonResponse(
        {
            "id": str(user.get("_id")),
            "full_name": user.get("full_name", ""),
            "age": user.get("age", 0),
            "profession": user.get("profession", ""),
            "city": user.get("city", ""),
            "education": user.get("education", ""),
            "height": user.get("height", ""),
            "religion": user.get("religion", ""),
            "mother_tongue": user.get("mother_tongue", ""),
            "bio": user.get("bio", ""),
            "verified": bool(user.get("verified", False)),
            "compatibility": user.get("compatibility") or 70,
            "interested": interested,
            "profile_pic": (
                user.get("profile_pic")
                and user.get("profile_pic_content_type")
                and ("data:" + user.get("profile_pic_content_type") + ";base64," + user.get("profile_pic"))
                or None
            ),
        }
    )



def wishlist_toggle_view(request, profile_id):
    """Toggle shortlist (wishlist) for current user.

    Frontend expects:
      POST /wishlist/toggle/<profile_id>/
      -> {"wishlisted": true/false}
    """
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"wishlisted": False})

    from_id = _get_request_user_object_id(request)
    if not from_id:
        return JsonResponse({"wishlisted": False})

    try:
        profile_oid = ObjectId(profile_id)
    except Exception:
        return JsonResponse({"wishlisted": False})

    users = get_users_collection()
    db = users.database

    wishlist = db.get_collection("wishlist")

    # Ensure index exists
    # Unique pair: (user_id, profile_id)
    from pymongo import ASCENDING
    wishlist.create_index([("user_id", ASCENDING), ("profile_id", ASCENDING)], unique=True)

    # If exists -> remove (toggle off). Otherwise -> insert.
    existing = wishlist.find_one({"user_id": from_id, "profile_id": profile_oid})
    if existing:
        wishlist.delete_one({"_id": existing["_id"]})
        return JsonResponse({"wishlisted": False})

    wishlist.insert_one(
        {
            "user_id": from_id,
            "profile_id": profile_oid,
            "created_at": datetime.utcnow(),
        }
    )
    return JsonResponse({"wishlisted": True})


def wishlist_count_view(request):
    """Return wishlist count for current user."""
    from django.http import JsonResponse

    if request.method != "GET":
        return JsonResponse({"count": 0})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"count": 0})

    users = get_users_collection()
    db = users.database
    wishlist = db.get_collection("wishlist")

    count = wishlist.count_documents({"user_id": user_oid})
    return JsonResponse({"count": count})


def wishlist_list_view(request):
    """Return full shortlisted profiles for current user."""
    from django.http import JsonResponse

    if request.method != "GET":
        return JsonResponse({"profiles": []})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"profiles": []})

    users = get_users_collection()
    db = users.database
    wishlist = db.get_collection("wishlist")

    # Get profile_ids first
    wish_docs = wishlist.find({"user_id": user_oid}).limit(200)
    out_profiles = []

    for wd in wish_docs:
        pid = wd.get("profile_id")
        if not pid:
            continue
        p = users.find_one({"_id": pid}) or {}
        out_profiles.append(
            {
                "id": str(pid),
                "full_name": p.get("full_name", ""),
                "age": p.get("age", ""),
                "profession": p.get("profession", ""),
                "city": p.get("city", ""),
                "education": p.get("education", ""),
                "height": p.get("height", ""),
                "religion": p.get("religion", ""),
                "mother_tongue": p.get("mother_tongue", ""),
                "bio": p.get("bio", ""),
                "verified": bool(p.get("verified", False)),
                "profile_pic_is_profile_pic": bool(p.get("profile_pic_is_profile_pic", False)),
                "profile_pic": p.get("profile_pic"),

                "profile_pic_content_type": p.get("profile_pic_content_type"),
                "compatibility": p.get("compatibility") or 70,
                "interested": False,
            }
        )

    return JsonResponse({"profiles": out_profiles})


def conversations_view(request):
    from django.http import JsonResponse


    if request.method != "GET":
        return JsonResponse({"conversations": []})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"conversations": []})

    users = get_users_collection()
    db = users.database
    chats = db.get_collection("conversations")

    convs = chats.find({"user_id": user_oid}).limit(50)
    out = []
    for c in convs:
        partner_oid = c.get("partner_id")
        partner = users.find_one({"_id": partner_oid}) or {}
        out.append(
            {
                "partner_id": str(partner_oid),
                "partner_full_name": partner.get("full_name", "Chat"),
            }
        )
    return JsonResponse({"conversations": out})


def messages_thread_view(request, partner_id):


    from django.http import JsonResponse


    if request.method != "GET":
        return JsonResponse({"messages": []})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"messages": []})

    users = get_users_collection()
    db = users.database
    messages_col = db.get_collection("messages")

    partner_oid = ObjectId(partner_id)

    # If users are blocked, return a blocked flag so UI can show a notice.
    if _is_blocked_mutual(db, user_oid, partner_oid):
        partner = users.find_one({"_id": partner_oid}) or {}
        return JsonResponse(
            {
                "partner_full_name": partner.get("full_name", ""),
                "blocked": True,
                "messages": [],
            }
        )

    partner = users.find_one({"_id": partner_oid}) or {}
    msgs = messages_col.find(

        {
            "$or": [
                {"sender_id": user_oid, "receiver_id": partner_oid},
                {"sender_id": partner_oid, "receiver_id": user_oid},
            ]
        }
    ).sort("created_at", 1).limit(200)

    out_msgs = [
        {"sender_id": str(m.get("sender_id")), "text": m.get("text", "")} for m in msgs
    ]

    return JsonResponse(
        {
            "partner_full_name": partner.get("full_name", ""),
            "messages": out_msgs,
        }
    )


def _is_blocked_mutual(db, user_oid, other_oid):
    blocks = db.get_collection("blocks")
    return bool(
        blocks.find_one({"user_id": user_oid, "blocked_id": other_oid})
        or blocks.find_one({"user_id": other_oid, "blocked_id": user_oid})
    )


def block_toggle_view(request, profile_id):
    """Mutual block/unblock.

    When A blocks B, we store two documents:
      - {user_id: A, blocked_id: B}
      - {user_id: B, blocked_id: A}

    Calling again will unblock both sides.
    """
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"blocked": False})

    from_id = _get_request_user_object_id(request)
    if not from_id:
        return JsonResponse({"blocked": False})

    try:
        other_oid = ObjectId(profile_id)
    except Exception:
        return JsonResponse({"blocked": False})

    if other_oid == from_id:
        return JsonResponse({"blocked": False})

    users = get_users_collection()
    db = users.database
    blocks = db.get_collection("blocks")

    # If either direction exists, treat as already blocked and unblock.
    already_blocked = bool(
        blocks.find_one({"user_id": from_id, "blocked_id": other_oid})
        or blocks.find_one({"user_id": other_oid, "blocked_id": from_id})
    )

    if already_blocked:
        blocks.delete_many({
            "$or": [
                {"user_id": from_id, "blocked_id": other_oid},
                {"user_id": other_oid, "blocked_id": from_id},
            ]
        })
        return JsonResponse({"blocked": False})

    # Insert mutual block rows (idempotent with insert_many).
    blocks.insert_many(
        [
            {"user_id": from_id, "blocked_id": other_oid, "created_at": datetime.utcnow()},
            {"user_id": other_oid, "blocked_id": from_id, "created_at": datetime.utcnow()},
        ]
    )

    # If these users were connected before blocking, remove the pinned connection
    # so Blocked users disappear from Connected/Interests.
    pinned = db.get_collection("pinned")
    pinned.delete_many({"user_id": from_id, "partner_id": other_oid})
    pinned.delete_many({"user_id": other_oid, "partner_id": from_id})

    # Remove from current user's shortlist (wishlist) if present.
    wishlist = db.get_collection("wishlist")
    wishlist.delete_many({"user_id": from_id, "profile_id": other_oid})


    return JsonResponse({"blocked": True})



def blocked_list_view(request):
    """Return profiles that current user has blocked (mutual rows).

    Response: { profiles: [ {id, full_name, age, ...} ] }
    """
    from django.http import JsonResponse

    if request.method != "GET":
        return JsonResponse({"profiles": []})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"profiles": []})

    users = get_users_collection()
    db = users.database
    blocks = db.get_collection("blocks")

    # We created mutual rows, so blocked people are where user_id=self and blocked_id=other.
    rows = blocks.find({"user_id": user_oid}, {"blocked_id": 1}).limit(200)
    other_ids = [r.get("blocked_id") for r in rows if r.get("blocked_id")]

    out = []
    for oid in other_ids:
        p = users.find_one({"_id": oid}) or {}
        out.append(
            {
                "id": str(oid),
                "full_name": p.get("full_name", ""),
                "age": p.get("age", ""),
                "profession": p.get("profession", ""),
                "city": p.get("city", ""),
                "education": p.get("education", ""),
                "height": p.get("height", ""),
                "religion": p.get("religion", ""),
                "mother_tongue": p.get("mother_tongue", ""),
                "bio": p.get("bio", ""),
                "verified": bool(p.get("verified", False)),
                "compatibility": p.get("compatibility") or 70,
            }
        )

    return JsonResponse({"profiles": out})


def messages_send_view(request, partner_id):
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"ok": False})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"ok": False})

    try:
        other_oid = ObjectId(partner_id)
    except Exception:
        return JsonResponse({"ok": False})

    users = get_users_collection()
    db = users.database
    if _is_blocked_mutual(db, user_oid, other_oid):
        return JsonResponse({"ok": False, "blocked": True})


    import json

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"ok": False})

    payload = {}
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    text = (payload.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False})

    users = get_users_collection()
    db = users.database
    messages_col = db.get_collection("messages")

    partner_oid = ObjectId(partner_id)

    messages_col.insert_one(
        {
            "sender_id": user_oid,
            "receiver_id": partner_oid,
            "text": text,
            "created_at": datetime.utcnow(),
        }
    )

    # Ensure conversation exists (both ways)
    conversations = db.get_collection("conversations")
    conversations.update_one(
        {"user_id": user_oid, "partner_id": partner_oid},
        {"$setOnInsert": {"user_id": user_oid, "partner_id": partner_oid, "created_at": datetime.utcnow()}},
        upsert=True,
    )
    conversations.update_one(
        {"user_id": partner_oid, "partner_id": user_oid},
        {"$setOnInsert": {"user_id": partner_oid, "partner_id": user_oid, "created_at": datetime.utcnow()}},
        upsert=True,
    )

    return JsonResponse({"ok": True})


def api_profiles_filter_view(request):
    """Return filtered profiles for the Matches advanced filters popup.

    Frontend calls: GET /api/profiles/?religion=...&profession=...&city=...

    Important behavior:
      - If the Matches filter form is empty, return the unfiltered list
        (only apply opposite-gender + exclude blocked users).

    Response shape:
      { "profiles": [ { id, full_name, age, profession, city, education, height,
                         religion, mother_tongue, bio, verified, compatibility,
                         wishlisted, interested, profile_pic } ... ] }
    """


    from django.http import JsonResponse

    if request.method != "GET":
        return JsonResponse({"profiles": []})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"profiles": []})

    # Current user's gender (to match opposite gender)
    users = get_users_collection()
    me = users.find_one({"_id": user_oid}) or {}
    my_gender = (me.get("gender") or "").lower()

    if my_gender == "male":
        target_gender = "female"
    elif my_gender == "female":
        target_gender = "male"
    else:
        target_gender = None

    def get_str(name: str):
        v = request.GET.get(name)
        if v is None:
            return None
        v = v.strip()
        return v or None

    religion = get_str("religion")
    profession = get_str("profession")
    city = get_str("city")
    education = get_str("education")
    mother_tongue = get_str("mother_tongue")
    height = get_str("height")

    age_min = get_str("age_min")
    age_max = get_str("age_max")

    salary_min = get_str("salary_min")
    salary_max = get_str("salary_max")

    # Build query
    query = {}

    # Detect empty filter form: if all supported filters are blank,
    # we should return an unfiltered matches list (still respecting
    # opposite-gender + exclude blocked users).
    has_any_filter = any(
        [
            bool(religion),
            bool(profession),
            bool(city),
            bool(education),
            bool(mother_tongue),
            bool(height),
            bool(age_min),
            bool(age_max),
            bool(salary_min),
            bool(salary_max),
        ]
    )


    # Exclude blocked users from results (so Dashboard/Matches never show blocked profiles)
    if user_oid:
        blocked_ids = _get_blocked_other_ids(users.database, user_oid)
        # Guard: if blocked_ids is empty or None, do nothing.
        if blocked_ids and len(blocked_ids) > 0:
            # Ensure types are correct for Mongo query (ObjectIds)
            query["_id"] = {"$nin": blocked_ids}


    if target_gender:
        query["gender"] = target_gender


    # If user provided at least one filter, apply advanced filters.
    # Otherwise, keep query limited to gender + blocked users.
    if has_any_filter:
        if religion:
            query["religion"] = {"$regex": religion, "$options": "i"}
        if profession:
            query["profession"] = {"$regex": profession, "$options": "i"}
        if city:
            query["city"] = {"$regex": city, "$options": "i"}
        if education:
            query["education"] = {"$regex": education, "$options": "i"}
        if mother_tongue:
            query["mother_tongue"] = {"$regex": mother_tongue, "$options": "i"}

        # Height is stored inconsistently (string vs numeric).
        # IMPORTANT: height values coming from UI like 5'10" are NOT floatable.
        # Keep it regex-based unless it's a clean numeric.
        if height:
            h = height.strip()
            # Treat only pure numeric strings as numeric.
            if h.replace(".", "", 1).isdigit():
                query["height"] = float(h)
            else:
                query["height"] = {"$regex": h, "$options": "i"}

        # Age range (safe parsing)
        try:
            if age_min:
                query.setdefault("age", {})
                query["age"]["$gte"] = int(age_min)
            if age_max:
                query.setdefault("age", {})
                query["age"]["$lte"] = int(age_max)
        except Exception:
            # ignore age filter parse issues
            pass

        # Salary range (safe parsing)
        salary_min_i = None
        salary_max_i = None
        try:
            if salary_min:
                salary_min_i = int(salary_min)
            if salary_max:
                salary_max_i = int(salary_max)
        except Exception:
            salary_min_i = None
            salary_max_i = None

        if salary_min_i is not None or salary_max_i is not None:
            salary_range = {}
            if salary_min_i is not None:
                salary_range["$gte"] = salary_min_i
            if salary_max_i is not None:
                salary_range["$lte"] = salary_max_i

            # Match either field.
            query["$or"] = [
                {"annual_salary": salary_range},
                {"salary": salary_range},
                {"annualIncome": salary_range},
            ]



    # Fetch results
    pinned = users.database.get_collection("pinned")
    wishlist = users.database.get_collection("wishlist")

    # Compute wishlisted set for this user
    wish_ids = wishlist.find({"user_id": user_oid}, {"profile_id": 1}).limit(200)
    wish_set = {w.get("profile_id") for w in wish_ids if w.get("profile_id")}

    # Use a conservative limit for performance
    cursor = users.find(query).limit(50)

    from .api_profiles import add_profile_fields

    profiles = []
    for p in cursor:
        profile_id = p.get("_id")
        if not profile_id:
            continue

        profiles.append(
            {
                **add_profile_fields(p),
                "wishlisted": bool(profile_id in wish_set),
                "interested": False,
            }
        )

    return JsonResponse({"profiles": profiles})


def messages_mark_seen_view(request):
    """Store last seen timestamp in session for chat unread counting.

    The frontend sends ISO8601 strings via JS. We normalize them into a
    strict ISO string that datetime.fromisoformat can parse back.
    """
    from django.http import JsonResponse
    if request.method != "POST":
        return JsonResponse({"ok": False})

    try:
        import json
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    last_seen_at = payload.get("lastSeenAt")
    if not last_seen_at:
        return JsonResponse({"ok": False})

    # Normalize to a format datetime.fromisoformat can parse reliably.
    # Example JS toISOString(): '2026-07-12T10:20:30.123Z' (ends with 'Z').
    try:
        if isinstance(last_seen_at, str) and last_seen_at.endswith("Z"):
            last_seen_at = last_seen_at[:-1] + "+00:00"

        dt = datetime.fromisoformat(last_seen_at)
        request.session["chat_last_seen_at"] = dt.isoformat()
        return JsonResponse({"ok": True})
    except Exception:
        # Fallback: store raw value (previous behavior)
        request.session["chat_last_seen_at"] = str(last_seen_at)
        return JsonResponse({"ok": True})



def messages_unread_count_view(request):
    """Return unread chat message count for current user.


    NOTE: The current Mongo schema for messages does not include read/unread flags.
    For now, we approximate unread count as number of messages received by the user
    since the last page load timestamp stored in session.

    Returns: {"count": int}
    """
    from django.http import JsonResponse

    if request.method != "GET":
        return JsonResponse({"count": 0})

    user_oid = _get_request_user_object_id(request)
    if not user_oid:
        return JsonResponse({"count": 0})

    users = get_users_collection()
    db = users.database
    messages_col = db.get_collection("messages")

    last_seen = request.session.get("chat_last_seen_at")
    if not last_seen:
        last_seen = None

    # If last_seen is stored as ISO string, convert to datetime; else treat as None.
    dt_last_seen = None
    if last_seen:
        try:
            dt_last_seen = datetime.fromisoformat(last_seen)
        except Exception:
            dt_last_seen = None

    query = {"receiver_id": user_oid}
    if dt_last_seen:
        query["created_at"] = {"$gt": dt_last_seen}

    count = messages_col.count_documents(query)
    return JsonResponse({"count": int(count)})


def debug_session_view(request):


    """Debug helper to inspect session state.

    Used to diagnose why /dashboard/ keeps redirecting to login.
    """

    from django.http import JsonResponse

    keys = list(request.session.keys())
    return JsonResponse(
        {
            "keys": keys,
            "has_user_id": bool(request.session.get("user_id")),
            "user_id": request.session.get("user_id"),
            "full_name": request.session.get("full_name"),
        }
    )




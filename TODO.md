# TODO - Fix 404 Errors

## Issues Found
1. Missing MEDIA_URL/MEDIA_ROOT in settings.py (referenced in urls.py)
2. Missing favicon.ico handling (browsers auto-request → 404)
3. Duplicate `path("", ...)` patterns in accounts/urls.py causing routing ambiguity
4. JS fetch calls could break with empty/invalid profile IDs

## Steps
### Step 1: Fix settings.py
- [x] Add MEDIA_URL and MEDIA_ROOT definitions

### Step 2: Fix vivah_project/urls.py
- [x] Add favicon.ico handler
- [x] Fix MEDIA_URL/MEDIA_ROOT static serving with proper guard

### Step 3: Fix accounts/urls.py
- [x] Remove duplicate `path("", views.edit_profile_view)` that shadows API URLs
- [x] Ensure API URL patterns are reachable (moved to separate urlpatterns + include)
- [x] Changed `edit_profile_root` named URL to `edit-profile-root/` prefix to avoid matching `/` exactly

### Step 4: Fix dashboard.html
- [x] Updated dropdown link from `edit_profile_root` → `edit_profile` (correct URL name)
- [x] Added defensive validation for profile IDs before making fetch calls (length check + ObjectId hex regex)


# TODO: Fix “Profile Pic not changing”

## What we found
- `edit_profile_view` saves `profile_pic` (base64) into MongoDB.
- But `edit_profile_view` does **not** pass `profile_pic` into `edit_profile.html` context.
- `edit_profile.html` always shows initials avatar; it never renders stored `profile_pic`.

## Steps to implement
1. Update `backend/accounts/views.py` `edit_profile_view`:
   - Fetch the logged-in user doc from MongoDB.
   - Include `profile_pic`, `profile_pic_content_type`, and `profile_pic_is_profile_pic` in the `user` dict passed to the template.
2. Update `frontend/templates/edit_profile.html`:
   - Show an `<img>` using `data:<content-type>;base64,<profile_pic>` when `profile_pic` exists.
   - Keep initials fallback when no pic exists.
3. (Optional) If after saving it still doesn’t show immediately, ensure template uses refreshed values and not only `request.session`.
4. Test:
   - Upload a new image.
   - Verify it appears on the same edit page after redirect.
   - Verify it appears in dashboard profile cards/modal if those rely on `profile_pic`.


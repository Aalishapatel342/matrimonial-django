# TODO

## Profile picture + avatar update (edit profile + navbar + cards)
- [ ] Update `backend/accounts/views.py` (`dashboard_view`) to pass current user's profile picture as a data-url (base64) to the template.
- [ ] Update `frontend/templates/dashboard.html` navbar avatar + dropdown header to show `<img>` when `profile_pic_data_url` exists; otherwise show initials.
- [ ] Update `frontend/templates/dashboard.html` profile card avatar blocks (for current user) if applicable (currently cards are for other profiles; still ensure consistency where full_name|initials is used).
- [ ] Update `frontend/templates/edit_profile.html` avatar on the left panel to:
  - click avatar to open the file picker
  - show uploaded image if present in context, else initials
- [ ] Ensure `edit_profile_view` passes `profile_pic_data_url` (or equivalent) in context to render correctly after loading edit page.
- [ ] Manual test: upload image in Edit Profile → submit → confirm navbar avatar changes to image (and no initials fallback unless no photo uploaded).


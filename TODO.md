# TODO

- [x] Implement backend connection status endpoint
  - [ ] Add `connection_status_view` in `backend/accounts/views.py`
  - [ ] Register route in `backend/accounts/api_urls.py`

- [x] Update dashboard frontend to sync main grid buttons after notification Accept/Decline
  - [x] Add `syncMainButtons()` in `frontend/templates/dashboard.html`
  - [x] Call it after `/interest/accept/.../` and `/interest/decline/.../`


- [ ] Manual testing checklist
  - [ ] Click Accept in Notifications; verify main grid shows “Connected” + pinned grid updates
  - [ ] Click Reject in Notifications; verify pinned grid unchanged + main button state correct


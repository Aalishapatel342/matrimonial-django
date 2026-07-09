# TODO

- [ ] Update dashboard backend so the Dashboard tab shows BOTH connected and not-connected profiles as requested, and add a UI filter that lets user switch between them.
- [ ] Update `frontend/templates/dashboard.html` to include a connected/not-connected filter (dropdown or toggle) and set it from query param.
- [ ] Update `backend/accounts/views.py` `dashboard_view()` to accept query param `connection_state` and apply correct MongoDB filtering based on `connections` and `interests`.
- [ ] Run Django dev server and manually verify: Dashboard shows both; selecting filters shows correct subsets; Interests tab still works.


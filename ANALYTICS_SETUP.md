# Trampu analytics

The board already receives aggregate email engagement from Resend, including delivered, opened and clicked recipients.

For site visits, connect the board's hourly updater to the Google Analytics 4 Data API using repository Actions secrets:

- `GA4_PROPERTY_ID`
- `GA4_SERVICE_ACCOUNT_JSON`

The intended board metrics are:

- Email clicks — recipients whose latest Resend event is `clicked`.
- Site visits — GA4 sessions for `trampu.online` over the last 7 days.
- Site users — GA4 total users for `trampu.online` over the last 7 days.
- Page views — GA4 page views for `trampu.online` over the last 7 days.

Only aggregate counts should be published to `data.json`; never publish names, email addresses, phone numbers, access tokens or service-account credentials.

# Certificate Code Generation Feature

## 1. Decision

Implement certificate-code generation in the authenticated Django/Unfold admin panel.

Do not expose certificate-code generation on a public page.

If a separate UI is needed later, it should be an authenticated staff portal, not a public academy page. The current project does not need a second UI for this feature.

## 2. Why Admin Is the Best Location

Certificate codes are part of the internal certificate issuance workflow. The admin panel already manages:

- Student names.
- Certificate PDFs.
- Certificate code slots.
- Existing certificate search.
- Certificate verification data.

Keeping generation in admin provides:

- Existing authentication and permissions.
- CSRF protection.
- A single place for code, student, and PDF management.
- Less duplicated UI and business logic.
- Lower risk of exposing internal issuance behavior.
- Easier auditing and support.

## 3. Option Comparison

| Option | Recommendation | Reason |
|---|---|---|
| Public generation page | Reject | Anyone could mint codes; it is an internal operation and creates abuse/security risks. |
| New unauthenticated academy UI page | Reject | It duplicates admin functionality and creates an unsafe certificate issuance surface. |
| New authenticated staff UI | Later option | Useful for bulk issuance or a larger back-office workflow, but unnecessary for the current model. |
| Existing Unfold Certificate admin | Recommended | Smallest change, best security boundary, and already manages the certificate fields. |

## 4. Proposed User Experience

### Certificate add page

Add a `Generate code` control next to each certificate code field:

- Generate code for certificate 1.
- Generate code for certificate 2.
- Generate code for certificate 3.

The generated value should be inserted into the selected form field but should not be persisted until the administrator saves the certificate record with its PDF.

The admin should still be able to enter a code manually for legacy records or externally issued certificates.

### Certificate change page

Provide the same controls when editing an existing certificate, but do not overwrite a non-empty code without an explicit confirmation.

Recommended behavior:

- Empty slot: generate immediately.
- Existing slot: show a confirmation before replacement.
- Existing saved code: never silently replace it.

### Verification URL preview

After the certificate is saved, show a read-only verification URL for each populated code:

```text
/certificate/<student-slug>-<code>/
```

Add a copy button for the URL. Generating QR images can be a later enhancement because the current project already has `generate_url_slug()` and existing QR assets/workflows.

## 5. Recommended Code Format

Use a stable prefix plus uppercase, non-ambiguous random characters.

Recommended example:

```text
FA7K3M9Q2
```

Format:

- Prefix: `FA`.
- Body: 8 random uppercase characters.
- Allowed body alphabet: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`.
- No hyphens, spaces, lowercase characters, or visually ambiguous `I`, `O`, `0`, and `1`.
- Maximum length remains safely below the current 50-character field limit.

Do not use a simple incremental counter as the public code. Sequential values such as `FA000001`, `FA000002`, and `FA000003` are easy to guess and make certificate enumeration easier.

Existing codes such as `FA0064` and `SR206` must remain valid. The new generator only controls newly generated values.

## 6. Generation Algorithm

Create a server-side helper, for example:

```text
generate_unique_certificate_code(prefix="FA")
```

The helper should:

1. Use `secrets.choice`, not the regular `random` module.
2. Build an uppercase code with the configured prefix.
3. Check all three certificate code columns case-insensitively.
4. Retry a bounded number of times if a collision is found.
5. Raise a clear internal error if the bounded retry limit is reached.
6. Return the code without saving it.

The helper must query all code slots:

```python
Q(certificate_code_1__iexact=code)
| Q(certificate_code_2__iexact=code)
| Q(certificate_code_3__iexact=code)
```

The final model save must still rely on the existing database uniqueness constraints and model validation. The generator is not a replacement for database protection.

## 7. Recommended Implementation Architecture

Keep the feature inside `certificate_app`. Do not move certificate functionality to `academy_app` and do not create a new Django app.

Recommended files:

```text
certificate_app/
  admin.py                 # admin controls and custom admin endpoint
  forms.py                 # optional custom CertificateAdmin form
  utils.py                 # code generation helper
  admin_urls.py            # optional, only if custom admin URLs are separated
  templates/admin/
    certificate_app/certificate/change_form.html  # optional admin override
  static/certificate_app/
    certificate_admin.js   # optional Generate/Copy controls
  tests.py                 # focused certificate generation tests
```

The smallest implementation can keep the custom admin endpoint and form logic in `certificate_app/admin.py`, but a dedicated `utils.py` makes the generator reusable and testable.

## 8. Admin Endpoint Design

The admin button needs server-side generation. Do not generate codes only in JavaScript.

Recommended endpoint:

```text
/admin/certificate_app/certificate/generate-code/
```

Properties:

- Registered through `CertificateAdmin.get_urls()`.
- Wrapped with `admin_site.admin_view()`.
- Accepts POST only.
- Requires authenticated staff permission.
- Uses CSRF protection.
- Returns JSON containing the generated code.
- Does not create a `Certificate` record.
- Does not accept an arbitrary code from the browser.

Example response:

```json
{
  "code": "FA7K3M9Q2"
}
```

The browser script inserts the response into the requested code field. The administrator must still save the certificate record and upload the corresponding PDF.

## 9. Permissions

The endpoint should require the same permission needed to add or change certificates:

- Add page: `certificate_app.add_certificate`.
- Change page: `certificate_app.change_certificate`.

Do not allow anonymous requests. Do not allow ordinary public users to call the endpoint.

If custom role permissions are introduced later, create a dedicated permission such as `generate_certificate_code`, but this is not necessary for the first implementation.

## 10. Data Model Recommendation

### First version: no migration

The first version should not add a model or database field. The existing three code fields already support the required workflow.

Advantages:

- No migration risk.
- Existing certificate records remain untouched.
- Existing verification URLs remain unchanged.
- Existing QR links remain valid.
- Smaller implementation and test surface.

### Future version: issuance audit log

If the business requires traceability, add a separate model later instead of changing `Certificate`:

```text
CertificateCodeGenerationLog
  code
  certificate
  created_by
  created_at
  source
  replaced_code
```

This should only be added when the organization needs a history of who generated, assigned, or replaced codes. It is not required for the initial feature.

## 11. Handling the Three Existing Slots

The generator should accept a slot number only for UI purposes:

- Slot 1 maps to `certificate_code_1`.
- Slot 2 maps to `certificate_code_2`.
- Slot 3 maps to `certificate_code_3`.

The server should validate that the requested slot is one of `1`, `2`, or `3`. It should never use a browser-provided field name without validation.

The generator should not automatically create certificate PDFs or assign codes to unrelated students.

## 12. Verification URL Behavior

The current certificate view extracts the final URL segment after the last hyphen. Therefore:

- Generated codes must not contain hyphens.
- Generated codes should remain URL-safe ASCII.
- The existing `generate_url_slug()` method should be reused.
- Both trailing-slash and no-trailing-slash certificate URLs must continue working.

Example:

```text
Student: Ahmed Ali
Code: FA7K3M9Q2
URL: /certificate/ahmed-ali-fa7k3m9q2/
```

## 13. Error Handling

The admin should show clear errors for:

- Unsupported HTTP method.
- Unauthenticated user.
- Missing or invalid slot.
- Collision after retry limit.
- Invalid code format if a manually entered code is used.
- Attempt to replace an existing code without confirmation.

Do not expose database errors or storage credentials in the JSON response.

## 14. Testing Plan

Add tests under `certificate_app/tests.py` or a focused certificate test module.

### Generator tests

- Generated value starts with `FA`.
- Generated value contains only the approved uppercase alphabet.
- Generated value contains no hyphen.
- Generated value fits within `max_length=50`.
- Existing codes are never returned.
- Case-insensitive collisions are rejected.
- The retry limit raises a controlled error.

### Model compatibility tests

- Existing manually entered codes continue to validate.
- Code normalization still produces uppercase values.
- Three code slots remain independently usable.
- Duplicate codes across slots are still rejected.
- Existing certificate lookup remains case-insensitive.

### Admin tests

- The generation endpoint requires login.
- The endpoint rejects GET if it is POST-only.
- The endpoint rejects invalid slots.
- The endpoint returns JSON for an authorized POST.
- The generated code is not saved before the certificate form is submitted.
- The existing certificate add/change pages remain usable.

### Regression tests

- Certificate URL without a trailing slash still returns 200.
- Certificate URL with a trailing slash still returns 200.
- Existing PDF links still render.
- Unknown certificate codes still return the existing not-found page.
- Existing QR-code URL formats remain valid.

## 15. Implementation Phases

### Phase 1: Generator service

- Add the approved format constants.
- Add the secure random generator.
- Add case-insensitive collision checks.
- Add unit tests.

### Phase 2: Admin endpoint

- Add the authenticated POST endpoint through `CertificateAdmin.get_urls()`.
- Add permission checks and CSRF protection.
- Add endpoint tests.

### Phase 3: Admin form controls

- Add Generate buttons for the three code fields.
- Add confirmation before replacing populated fields.
- Add copy-to-clipboard behavior.
- Add translated labels and accessible button names.

### Phase 4: Verification URL preview

- Show the generated verification URL after the record is saved.
- Add a safe copy button.
- Optionally add QR generation in a separate feature.

### Phase 5: Production verification

- Run migrations if any future audit model is added.
- Run `manage.py check`.
- Run certificate and academy tests.
- Test both existing certificate URL forms.
- Test admin permissions with staff and superuser accounts.
- Test local and R2 storage without changing certificate PDF behavior.

## 16. What Should Not Be Done

- Do not create a public code-generation page.
- Do not let JavaScript generate codes without a server collision check.
- Do not replace existing certificate codes automatically.
- Do not change the certificate URL parser.
- Do not move certificate models into `academy_app`.
- Do not add WhatsApp or academy homepage fields to `AppSettings`.
- Do not replace the three existing code fields in the first version.
- Do not use sequential predictable codes as the public verification identifier.
- Do not expose the admin generation endpoint outside authenticated admin access.

## 17. Final Recommendation

Build an explicit, server-side `Generate code` control inside the existing Unfold `CertificateAdmin` form. Use secure random uppercase codes such as `FA7K3M9Q2`, collision-check all three existing certificate code fields, and save the value only when the administrator saves the certificate record.

Do not create a public UI page. Consider a separate authenticated staff interface only if future requirements include bulk issuance, certificate lifecycle management, audit history, or advanced reporting.

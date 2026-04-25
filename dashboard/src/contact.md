---
title: Contact
---

# Contact Insight Softmax

[Insight Softmax](https://insightsoftmax.com/) is a software company focused on applied quantum computing and AI infrastructure. We'd love to hear from you — whether you have questions about this benchmarking project, are interested in working together, or want to explore what quantum computing can do for your organisation.

<div style="display: grid; grid-template-columns: 1fr 1.6fr; gap: 3rem; margin: 2rem 0; align-items: start;">

<div>

## Offices

### US

**San Francisco**
1 Embarcadero Center, Suite 1200
San Francisco, CA 94111

+1 628-225-2115
[info@insightsoftmax.com](mailto:info@insightsoftmax.com)

### EU

**Zürich**
Hardturmstrasse 123
8005 Zürich

+41 77 279 66 10
[info@insightsoftmax.ch](mailto:info@insightsoftmax.ch)

</div>

<div>

## Send a message

<form id="contact-form" class="contact-form">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
    <div class="form-row">
      <label for="first-name">First Name</label>
      <input id="first-name" type="text" name="First Name" placeholder="First name">
    </div>
    <div class="form-row">
      <label for="last-name">Last Name</label>
      <input id="last-name" type="text" name="Last Name" placeholder="Last name">
    </div>
  </div>
  <div class="form-row">
    <label for="email">Email <span style="font-weight:300;color:var(--isc-muted);text-transform:none">(required)</span></label>
    <input id="email" type="email" name="Email" required placeholder="you@example.com">
  </div>
  <div class="form-row">
    <label for="message">Message</label>
    <textarea id="message" name="Message" rows="7" placeholder="How can we help?"></textarea>
  </div>
  <div id="form-error" style="display:none;color:#c0392b;font-size:0.85rem;margin-top:-0.25rem"></div>
  <button type="submit" id="contact-submit" class="contact-submit">Send message →</button>
</form>
<div id="contact-success" style="display:none;font-size:1.05rem;color:var(--isc-text);padding:1rem 0">
  Thanks for contacting us! We will get in touch with you shortly.
</div>

<script>
document.getElementById('contact-form').addEventListener('submit', async function(e) {
  e.preventDefault();
  const form = e.target;
  const btn = document.getElementById('contact-submit');
  const error = document.getElementById('form-error');

  btn.disabled = true;
  btn.textContent = 'Sending…';
  error.style.display = 'none';

  try {
    const res = await fetch('https://formspree.io/f/xlgalnnk', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify(Object.fromEntries(new FormData(form))),
    });
    if (res.ok) {
      form.style.display = 'none';
      document.getElementById('contact-success').style.display = 'block';
    } else {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || 'Submission failed');
    }
  } catch (err) {
    error.textContent = 'Something went wrong. Please try again or email us directly at info@insightsoftmax.com.';
    error.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Send message →';
  }
});
</script>

</div>
</div>

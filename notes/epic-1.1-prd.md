<html><head></head><body><h3>Story 1.1 </h3>
<hr>
<h2>1. Entity menu (MVP for 4.1)</h2>

| Label       | Scope                               | Regex sketch                                       | Notes                                                                                                                      |
| ----------- | ----------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| EMAIL       | RFC 5322 subset                     | [\w.+-]+@[\w-]+\.[\w.-]{2,}                        | Good enough for 99 % of mail; avoids huge RFC monsters. (Regex validation of email addresses according to RFC5321/RFC5322) |
| PHONE       | NANP 10-digit                       | (?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4} | Accepts 555-555-5555, (555) 555-5555, +1 555 555 5555. (Regular expression to match standard 10 digit phone number)        |
| SSN         | U.S. social security                | \b\d{3}-\d{2}-\d{4}\b                              | Rejects “000-” starts & “666”. (Add later if needed.)                                                                      |
| CREDIT_CARD | Visa/Mastercard/AmEx                | `\b(?:4\d{12}(?:\d{3})?                            | 5[1-5]\d{14}                                                                                                               |
| IP_ADDRESS  | IPv4 + v6                           | `(?:\b\d{1,3}(?:.\d{1,3}){3}\b                     | (?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4})`                                                                                 |
| DOB         | Dates like MM/DD/YYYY or YYYY-MM-DD | `\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}                | \d{4}-\d{2}-\d{2})\b`                                                                                                      |
| ZIP         | US ZIP / ZIP+4                      | \b\d{5}(?:-\d{4})?\b                               | Locale-specific; extend with postcodes later.                                                                              |

<p><em>All patterns compiled with <code inline="">re.IGNORECASE | re.MULTILINE</code> and wrapped in <code inline="">r''</code> raw strings.</em></p>
<hr>
<h2>2. Return-value schema</h2>
<h3>2.1 Keep the <em>dict-of-lists</em> for backward compatibility</h3>
<pre><code class="language-python">from typing import Dict, List

Annotation = Dict[str, List[str]]

# e.g. {"EMAIL": ["[email protected]"], "PHONE": ["555-555-5555"]}

</code></pre>

<h3>2.2 Offer an optional structured model (new but additive)</h3>
<pre><code class="language-python">from pydantic import BaseModel
from typing import List

class Span(BaseModel):
label: str # "EMAIL"
start: int # char offset
end: int # char offset
text: str

class AnnotationResult(BaseModel):
text: str
spans: List[Span]
</code></pre>

<p><em>Why both?</em> Existing users don’t break; new users get richer data. The regex annotator returns <strong>both</strong>:</p>
<pre><code class="language-python">regex_result = {lbl: [s.text for s in spans_by_label[lbl]] for lbl in spans_by_label}
return regex_result, AnnotationResult(text=input_text, spans=all_spans)
</code></pre>
<p><code inline="">TextService</code> will pick whichever format the caller asked for.</p>
<hr>
<h2>3. Performance budget</h2>
<ul>
<li>
<p>Target ≤ 20 µs / kB on a MacBook M-series at -O.</p>
</li>
<li>
<p>Compile all patterns once at module import.</p>
</li>
<li>
<p>Run <code inline="">re.finditer</code> for each pattern, append spans; no pandas, no multiprocessing.</p>
</li>
</ul>
<hr>
<h2>4. Edge-case policy</h2>
<ul>
<li>
<p><strong>False positives &gt; false negatives</strong> for v 1: easier to redact extra than miss PII.</p>
</li>
<li>
<p>No validation (e.g., Luhn) in 4.1.0; add later under a <code inline="">validate=True</code> flag.</p>
</li>
<li>
<p>Reject obviously invalid IPv4 octets (<code inline="">25[6-9]</code>, <code inline="">3\d{2}</code>) to keep noise down.</p>
</li>
</ul>
<hr>
<h2>5. Acceptance checklist (feeds Story 1.4 baseline)</h2>
<ul class="contains-task-list">
<li class="task-list-item">
<p><input type="checkbox" disabled=""> All patterns compile.</p>
</li>
<li class="task-list-item">
<p><input type="checkbox" disabled=""> Unit tests pass on happy-path and tricky strings (<code inline="">foo@[123.456.789.000]</code> should fail).</p>
</li>
<li class="task-list-item">
<p><input type="checkbox" disabled=""> Benchmarks show regex path at least <strong>5× faster</strong> than spaCy on 10 kB sample.</p>
</li>
<li class="task-list-item">
<p><input type="checkbox" disabled=""> Output dict keys exactly match label names above.</p>
</li>
</ul>
</body></html>

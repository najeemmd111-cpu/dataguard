// n8n Code node: turn DataGuard alert events into one email (and an optional Slack message).
// The rules engine POSTs {summary, events, dashboard_url, ...}; the Webhook node puts it in `body`.
const body = $input.first().json.body ?? $input.first().json;
const events = body.events ?? [];
const summary = body.summary ?? {};

const icon = { failing: '❌', recovered: '✅', test: '🧪' };
const label = { failing: 'FAILING', recovered: 'RECOVERED', test: 'TEST' };
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

function line(e) {
  const numbers = e.measured_value ? ` (measured ${e.measured_value}, allowed ${e.threshold})` : '';
  return `${icon[e.type]} ${label[e.type]} [${e.severity}] ${e.dataset} / ${e.rule_id}: ${e.message ?? ''}${numbers}. ` +
    `Owner: ${e.owner}. Open: ${e.dataset_url}`;
}

const failing = events.filter((e) => e.type === 'failing');
const recovered = events.filter((e) => e.type === 'recovered');
const tests = events.filter((e) => e.type === 'test');

let subject;
if (events.length === 1) {
  const e = events[0];
  subject = `DataGuard: ${e.dataset}/${e.rule_id} ${e.type === 'recovered' ? 'recovered' : e.type === 'test' ? 'test alert' : `is failing (${e.severity})`}`;
} else {
  const parts = [];
  if (failing.length) parts.push(`${failing.length} rule${failing.length > 1 ? 's' : ''} failing`);
  if (recovered.length) parts.push(`${recovered.length} recovered`);
  if (tests.length) parts.push(`${tests.length} in a test alert`);
  subject = `DataGuard: ${parts.join(', ')}`;
}

const stillFailing = summary.still_failing
  ? `\n${summary.still_failing} other rule(s) are still failing from earlier runs.`
  : '';
const text = [...events.map(line), stillFailing, `\nDashboard: ${body.dashboard_url ?? ''}`].join('\n').trim();

const rows = events.map((e) => `
  <tr>
    <td>${icon[e.type]} <strong>${label[e.type]}</strong></td>
    <td>${esc(e.severity)}</td>
    <td><a href="${esc(e.dataset_url)}">${esc(e.dataset)} / ${esc(e.rule_id)}</a></td>
    <td>${esc(e.message)}${e.measured_value ? `<br><small>measured ${esc(e.measured_value)}, allowed ${esc(e.threshold)}</small>` : ''}</td>
    <td>${esc(e.owner)}</td>
  </tr>`).join('');
const html = `<div style="font-family: Arial, sans-serif">
  <h2 style="margin:0 0 12px">${esc(subject)}</h2>
  <table cellpadding="6" style="border-collapse:collapse" border="1">
    <tr><th>Event</th><th>Severity</th><th>Rule</th><th>Details</th><th>Owner</th></tr>${rows}
  </table>
  ${stillFailing ? `<p>${esc(stillFailing.trim())}</p>` : ''}
  <p><a href="${esc(body.dashboard_url)}">Open the DataGuard dashboard</a></p>
</div>`;

// Slack only for rules that just started failing with critical severity, and only if a webhook is set.
const critical = failing.filter((e) => e.severity === 'critical');
const slackUrl = $env.SLACK_WEBHOOK_URL || '';
const slackText = critical.map(line).join('\n');

return [{
  json: {
    subject,
    text,
    html,
    to: $env.ALERT_EMAIL_TO || 'data-team@example.com',
    mailpitUrl: ($env.MAILPIT_URL || 'http://mailpit:8025').replace(/\/$/, ''),
    sendSlack: critical.length > 0 && slackUrl !== '',
    slackUrl,
    slackText,
    events: events.length,
  },
}];

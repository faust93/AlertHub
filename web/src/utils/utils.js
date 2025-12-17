export function isValidTimeZone(tz) {
  try {
    Intl.DateTimeFormat(undefined, { timeZone: tz })
    return true
  } catch (e) {
    return false
  }
}

export function convertIsoToCustomFormatLocal(isoString) {
  if(!isoString) return ''
  const date = new Date(isoString);
  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Mar", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const month = monthNames[date.getMonth()];
  const day = date.getDate();
  const year = date.getFullYear();
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  return `${month} ${day}, ${year} ${hours}:${minutes}:${seconds}`;
}

export function convertIsoToCustomFormat(isoString) {
  if(!isoString) return ''
  const tz = localStorage.getItem('user_tz') === 'Local' 
    ? Intl.DateTimeFormat().resolvedOptions().timeZone 
    : localStorage.getItem('user_tz') || Intl.DateTimeFormat().resolvedOptions().timeZone

    const date = new Date(isoString)
  const options = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: tz,
    hour12: true,
  };

  const formatter = new Intl.DateTimeFormat('en-US', options)
  const parts = formatter.formatToParts(date)
  const get = type => parts.find(p => p.type === type)?.value

  const month = get('month')
  const day = get('day')
  const year = get('year')
  const hours = get('hour')
  const minutes = get('minute')
  const seconds = get('second')

  return `${month} ${day}, ${year} ${hours}:${minutes}:${seconds}`
}

export function convertEpochToCustomFormat(unixEpoch) {
    const date = new Date(unixEpoch).toISOString()
    return convertIsoToCustomFormat(date)
}

export function getDurationString(dateString1, dateString2) {
  const date1 = new Date(dateString1);
  const date2 = new Date(dateString2);
  const totalMs = Math.abs(date2 - date1);

  const DAY = 24 * 60 * 60 * 1000;
  const HOUR = 60 * 60 * 1000;
  const MINUTE = 60 * 1000;
  const SECOND = 1000;

  let msCopy = totalMs;

  const days = Math.floor(msCopy / DAY);
  msCopy %= DAY;

  const hours = Math.floor(msCopy / HOUR);
  msCopy %= HOUR;

  const minutes = Math.floor(msCopy / MINUTE);
  msCopy %= MINUTE;

  const seconds = Math.floor(msCopy / SECOND);

  const parts = [];
  if (days > 0) parts.push(`${days}days`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (seconds > 0) parts.push(`${seconds}s`);

  return parts.length > 0 ? parts.join(' ') : '0s';
}

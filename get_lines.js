const fs = require('fs');
const content = fs.readFileSync('./Anime Synchro Tracker v11.0.1.html', 'utf8');
const scriptMatch = content.match(/<script>(.*?)<\/script>/s);
const scriptContent = scriptMatch[1];
const lines = scriptContent.split('\n');
console.log(lines.slice(380, 395).map((l, i) => `${381 + i}: ${l}`).join('\n'));

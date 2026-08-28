const fs = require('fs');
const html = fs.readFileSync('Anime Synchro Tracker v11.0.1.html', 'utf8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (scriptMatch) {
    fs.writeFileSync('extracted.js', scriptMatch[1]);
    console.log('Extracted JS to extracted.js');
} else {
    console.log('No script tag found');
}

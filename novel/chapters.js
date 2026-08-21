---
layout: null
permalink: /novel/chapters.js
---
window.NOVEL_CHAPTERS = [
  {% for ch in site.data.novel_chapters %}
  { "num": {{ ch.num }}, "title": {{ ch.title | jsonify }}, "file": {{ ch.file | jsonify }} }{% unless forloop.last %},{% endunless %}
  {% endfor %}
];

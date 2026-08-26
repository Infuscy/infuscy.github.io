---
layout: null
permalink: /fire-to-future/chapters.js
---
window.FIRE_TO_FUTURE_CHAPTERS = [
  {% for ch in site.data.fire_to_future_chapters %}
  { "type": {{ ch.type | jsonify }}, "num": {{ ch.num | jsonify }}, "title": {{ ch.title | jsonify }}, "part": {{ ch.part | jsonify }}, "file": {{ ch.file | jsonify }}, "label": {{ ch.label | jsonify }} }{% unless forloop.last %},{% endunless %}
  {% endfor %}
];

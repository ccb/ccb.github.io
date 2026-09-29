---
title: Chris Callison-Burch
layout: default
img: CCB-small.jpg
img_link: assets/img/CCB.jpeg
caption: |
 <b>Email:</b> ccb@upenn.edu<br />
 <b>Office:</b> AGH 420<br />
 <b>Office Hours:</b> Wednesdays 3:30-5pm in AGH 431 (Fall 2026)<br />
active_tab: main_page 
keep_sidebar: true 
---
Chris Callison-Burch is the Raj and Neera Singh Professor of Artificial Intelligence in the Department of Computer and Information Science at the University of Pennsylvania.

His research is in natural language processing. His group currently works on using large language models to verify scientific claims, on measuring bias and framing in news coverage at scale, and on synthetic data for training and evaluating open models. He is the principal investigator of the DARPA SciFy program at Penn and co-chairs the Human-AI Symbiosis working group of the [NSF AI Institute for Human-AI Cooperation](https://www.nsf.gov/awardsearch/show-award/?AWD_ID=2433450). His work has also been funded by IARPA and by faculty research awards from Google, Microsoft, Amazon, Meta, and Roblox. He was a visiting research scientist at the Allen Institute for AI in 2023 and 2024.

He teaches Penn's Artificial Intelligence course, which enrolled more than 600 students across its on-campus and online sections in Fall 2025. In 2026 he received the Lindback Award for Distinguished Teaching, the university's highest teaching honor, following the Lutron Spira Award for Excellence in Teaching and Advising and two Ford Motor Company Awards for Faculty Advising.

Fifteen PhD students have graduated from his lab. They hold faculty positions at Brown, Carnegie Mellon, and Drexel, research positions at Google, Amazon, Bloomberg, and the Johns Hopkins Human Language Technology Center of Excellence, and have founded several companies.

He has published more than 250 papers, which have been cited over 40,000 times. He is a Sloan Research Fellow, served as General Chair of ACL 2017 and Program Co-Chair of EMNLP 2015, and was the ACL's Sponsorship Director from 2020 to 2025. In 2023 he [testified before Congress](https://www.youtube.com/playlist?list=PL0S5TKwqfRKKUNWzp7rEe5uuLV-o9VC2f) on generative AI and copyright law.

<!--
<b>Promotion Materials</b>

I'm going up for promotion to Full Professor this year.  If you'd like to see my materials here they are:

<ul>
<li> <a href="resume.html" class="label label-primary">CV</a> </li>
<li> <a href="research-statement.html" class="label label-success">Research Statement</a> </li>
<li> <a href="teaching-statement.html" class="label label-warning">Teaching Statement</a> </li>
<li> <a href="promotion-summary.html" class="label label-danger">Highlights</a> </li>
</ul>
-->



<b>Recent Papers</b>

<ol>
    {% assign recent_papers = site.data.publications | where: "featured", true | slice: 0, 5 %}
    {% for pub in recent_papers %}
        {% assign author_list = pub.authors | split: ", " %}
        {% if author_list.size > 10 %}
            {% assign author_display = author_list | slice: 0, 5 | join: ", " | append: ", et al." %}
        {% else %}
            {% assign author_display = pub.authors %}
        {% endif %}
        {% if pub.url %}
            <li> <a href="{{ pub.url }}">{{ pub.title }}</a>. {{ author_display }}. <em>{{ pub.venue }}</em>, {{ pub.year }}.{% if pub.award and pub.award != "" %} <span class="label label-success">{{ pub.award }}</span>{% endif %} </li>
        {% else %}
            <li> {{ pub.title }}. {{ author_display }}. <em>{{ pub.venue }}</em>, {{ pub.year }}.{% if pub.award and pub.award != "" %} <span class="label label-success">{{ pub.award }}</span>{% endif %} </li>
        {% endif %}
    {% endfor %}
</ol>


<b>Recent Press</b>

<ol>
    {% assign recent_press = site.data.press | slice: 0, 5 %}
    {% for press in recent_press %}
        {% if press.url %}
            <li>
                 <a href="{{ press.url }}">{{ press.source }}."{{ press.title }}" by {{ press.by_line }}.</a>  {{ press.date }} </li>
        {% endif %}
    {% endfor %}
</ol>


<b>Recent Talks</b>

<ol>
    {% assign recent_talks = site.data.talks | slice:0,5 %}
    {% for talk in recent_talks %}
      {% if talk.url %}
        <li> <a href="{{talk.url}}">{{ talk.venue }}. {{talk.title}}</a>. {{talk.date}} </li>
      {% else %}
        <li> {{ talk.venue }}. {{talk.title}}. {{talk.date}} </li>
      {% endif %}
  {% endfor %}
</ol>

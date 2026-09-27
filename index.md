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
Chris Callison-Burch is the Raj and Neera Singh Professor of Artificial Intelligence at the University of Pennsylvania. His course on Artificial Intelligence has one of the highest enrollments at the university with over 500 students taking the class each Fall. 

He is best known for his research into natural language processing.  His current research is focused on applications of large language models to long-standing challenges in artificial intelligence.

Prof Callison-Burch has more than 200 publications, which have been cited over 35,000 times. He is a Sloan Research Fellow, and he has received faculty research awards from Google, Microsoft, Amazon, Facebook, and Roblox, in addition to funding from DARPA, IARPA, and the NSF. 

In 2023, Prof. Callison-Burch [testified before congress](https://www.youtube.com/playlist?list=PL0S5TKwqfRKKUNWzp7rEe5uuLV-o9VC2f) about the relationship of generative AI and Copyright Law.

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

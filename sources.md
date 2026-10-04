# Content Sources

This file describes which official ReDI sources the chatbot is allowed to use. The sources themselves are listed in `data/sources.json`. If a source isn't marked **Yes** there, the chatbot doesn't use it.

## 1. Topics to cover

Tick a topic once at least one included source covers it.

- [ x ] What ReDI is and its mission
 => https://www.redi-school.org/
- [ x ] Courses offered 
=> https://www.redi-school.org/course-finder
- [ x ] Who can join, and whether it costs anything 
=> https://www.redi-school.org/course-finder
- [ x ] How to apply and the deadlines 
=>  https://www.redi-school.org/web-development/munich/dcp/coding-with-ai
- [ x ] Locations 
 => https://www.redi-school.org/
- [ x ] Course format (online or in person, schedule, language) 
=> https://www.redi-school.org/course-finder
- [ x ] Volunteering or teaching 
=> https://www.redi-school.org/become-a-volunteer-at-redi-school
- [ x ] Partnering or donating 
=> https://www.redi-school.org/support-redi
- [ x ] Contact
 => https://www.redi-school.org/contact
- [ x ] Career support
 => https://www.redi-school.org/our-career-support

## 2. Inclusion rules

A source is included only if it is:

- **Official and public:** ReDI's own content that anyone can see
- **Stable:** not news, blog posts or events that go out of date quickly
- **In English:** an English version exists (the MVP is English only)
- **Not a duplicate:** if two sources say the same thing, keep the better one

The limit is **10–25 included sources**.

## 3. Sources

The list of sources is in `data/sources.json`, one entry per page with these fields:

- **url, title**
- **category:** one of About ReDI, Courses, Applications, Locations, Volunteering, Career Support, Support ReDI, Contact
- **language, audience**
- **include:** Yes, No or Maybe. Only Yes sources are ingested.
- **notes:** anything worth knowing about the page. When include is No, the reason goes here (for example "out of date" or "duplicate of Course Finder").

`tests/test_sources.py` checks the rules from section 2 and the checklist in section 6, so run the tests after editing the file.

## 4. Documents to request

Official documents that aren't on the website, such as FAQs, handbooks and application guides.

| Document | Ask whom | Status | Notes |
|----------|----------|--------|-------|
| PDF      | Luciana  | wait for responce! |
| | | | |

## 5. Gaps

These are topics with no good official source. The chatbot should answer "I don't know" for them, and they go into the Task 2 test questions as unanswerable questions.

- Questions:
Does ReDI provide laptops to every student? (Partly answered by Women Courses: Digital Women Program only)
Can ReDI help me find an apartment in Munich?
Will I get a job after completing a ReDI course?
What salary will I earn after finishing a ReDI course?
Can ReDI guarantee me an internship?
Can ReDI help me with my visa or residence permit?
Can ReDI pay for my transportation to the school?
Which teacher will teach my course next semester?
How many students will be in my class next semester?
Can I receive financial support from ReDI while studying?

- Answer:
"I couldn't find reliable information about this in the available ReDI sources.”


## 6. Done checklist

- [ x ] Every topic in section 1 is either covered or listed in section 5
- [ x ] 10–25 sources are marked **Yes**
- [ x ] Every included source has a working URL or file name
- [ x ] Every excluded source has a reason in Notes

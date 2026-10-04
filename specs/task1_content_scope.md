# Task 1 – Define Initial Content Scope

## Scenario 1: Add a source to the content scope

**Given** an approved ReDI source is available  
**When** the source is added to the initial content scope  
**Then** the title, URL or document reference, category, language, target audience, and last-updated date should be recorded.

---

## Scenario 2: Handle a missing last-updated date

**Given** an approved ReDI source has no available last-updated date  
**When** the source is added to the content scope  
**Then** the last-updated date should be marked as unavailable.

---

## Scenario 3: Cover the required categories

**Given** the initial source list has been created  
**When** the content scope is reviewed  
**Then** it should cover About ReDI, Courses, Applications, Locations, Volunteering, Career Support, Support ReDI, and Contact.

---

## Scenario 4: Cover both target audiences

**Given** the initial source list has been created  
**When** the content scope is reviewed  
**Then** it should include information relevant to both prospective and current students.

---

## Scenario 5: Handle topics without a reliable source

**Given** no reliable or approved ReDI source is available for a topic  
**When** the content scope is reviewed  
**Then** the topic should be marked as not covered.
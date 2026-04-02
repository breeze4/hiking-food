# Food Planning Agent Design Interview — 2026-04-01

Record of user responses during the /grill-me design session for the food planning agent feature.

---

## Q1: Is the agent's job to produce a complete trip_snacks + trip_meals selection that hits the calorie/weight targets?

> ideally yes - I want a complete plan and then I want to be able to provide feedback and have the agent self-improve with my preferences each time

## Q2: Where does the agent run? (CLI vs web UI)

> CLI first - I will run this agent from Claude Code

## Q3: Do those categories feel right? Would you merge or split any?

(Proposed 5 categories: Drink mixes, Lunch, Salty, Sweet, Bars/Energy)

> that seems like a great start - yes i like the 5 categories for snacks - "lunch" can be for things like peanut butter and cheese, tortillas, etc

## Q4: For a 7-day trip, how do you think about meal variety?

> the output of all this btw for the packing stage is into individual ziplocks mainly
>
> to answer q4:
>
> I actually almost always will have just one or two types of breakfasts - I am all about kashi golean, frozen strawberries, powdered milk, add whatever sorts of nuts, dates, seeds, dried fruit - to eat cold with filtered water added - I might do granola or golean, but same idea for both
>
> for dinners, I think 2-3 is right. I think like 2 noodles, 1 rice/bean, 1 rice/dehydrated meat for a 4 dinner trip. No one thing should be more than half the trip, how about that as a rule? - on a 7 day trip I might do 3 ramen with some different toppings; 2 rice/beans; 2 rice/dehydrated meat
>
> I really want to find ways to minimize ingredients needed, while keeping things interesting

## Q5: Your breakfasts don't match the Skurka recipes at all, do they? Should the agent use Skurka breakfasts or your actual breakfast template?

> the skurka recipes are things on my shelf I know are great and worth trying - I personally am using my own variants of them; I dont think I need the complexity of a template system, thats just how I think about it; in practice I will have a manageable set of recipes to pick from and its my own curation problem if they get out of control - I can always add new features then if needed

## Q6: Same question for dinners — fixed recipes or templates with interchangeable components?

> fixed recipes

## Q7: How do you actually eat during a hiking day?

> yeah I have made the mistake of packing too much variety of snacks - hard to prep, sometimes you wish you had more of specific ones and less of others; I find I hoard snacks, so if I think this is the only one I'll ever have, I will save it. I prefer to eat the good food soon and not save too much "good" stuff.
>
> meal slots are actually a great idea - no evening snack, that would be with dinner; I actually want to add that as a feature to the app itself so then the agent can just fill those in;

## Q8: Let's define the meal slots. What goes in each?

(Proposed: Breakfast, Morning snack, Lunch, Afternoon snack, Dinner)

> yes exactly, so I can have a little meter for my trip with buckets for each of the categories and I can see at a glance on a heatmap which day doesnt have food selected for a spot - so its basically meters per slot and how many days were accounted for by the plan thus far (as I add foods to the plan, it raises/lowers the meters)

## Q9: So a snack on a trip would now belong to a slot? And drink mixes would be... slotless?

> drink mixes are configurable per day with a separate input - normally 2/day

## Q10: When the agent assigns "7x Kind bars" to the morning snack slot — does that mean one per morning, or is it calorie-based?

> so its like the bucket of calories allocated for that slot per day is filled - the buckets for snacks are variable and based on the dinners and breakfasts - does that make sense?

## Q11: How should the remaining calories split across the three snack slots?

(Proposed options: equal thirds, weighted, user-configurable)

> yeah I think 25/40/35 could work as a baseline? we can save this as a feature request to make this more intuitive and customizable

## Q12: How far should the agent go to minimize the shopping list? Primary driver or tiebreaker?

> yes tiebreaker sounds good - save a future feature request to have alternates built-in to the plan so there can be options within the plan, but thats future

## Q13: Until ratings exist in the app, how should the agent learn your preferences?

(Proposed: A) conversation memory only, B) notes field, C) both)

> yes C sounds good, then we can add preferences as the most weighted one

## Q14: When the agent proposes a plan, what should the output look like?

> it should use the API and create a plan in there using all the features

## Q15: So the workflow is: read trip, build plan via API, you review in app, give feedback, agent adjusts?

(Confirmed the full loop)

## Q16: Should the agent clear existing selections first, or build on top of what's already there?

> lets say it asks - but I think the answer would be yes and then replace whats there with the proposed plan, yknow?

(Clarified in follow-up:)

> I actually do think it should start with whats currently there and then build on that - do a pass of refining the whole thing anyways so you'll find weird stuff that way - make sense?

## Q17: Full design playback — what's wrong or missing?

(No objections to the playback. Confirmed the design.)

## Q18: Does the agent need snack categories and meal slots built into the app first, or can it work without them?

> yes that makes sense to me - we can back-port the agent to use the API when available

---

## Key decisions summary

- Agent runs from CLI (Claude Code), talks to beebaby API
- Fixed recipes, user curates the library
- Breakfasts: 1-2 types repeated (cold cereal, not Skurka)
- Dinners: 2-3 unique, no single recipe > half the trip
- 5 snack categories: drink mixes, lunch, salty, sweet, bars/energy
- 3 snack slots: morning (25%), lunch (40%), afternoon (35%)
- Drink mixes: separate daily config, default 2/day
- Fewer items, more servings — anti-hoarding philosophy
- Shopping list minimization as tiebreaker
- Preferences: ratings (future) > catalog notes > conversation memory
- Agent starts from current trip state, refines the whole plan
- Agent v1 works without app changes, carries knowledge in prompt
- Packing output is into individual ziplocks

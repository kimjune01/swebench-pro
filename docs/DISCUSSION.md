# Discussion

The result tables report what happened. This page reads them, and the reading carries opinion the tables do not. The two stay apart on purpose: every number here recomputes from the committed ledgers and stands without interpretation, and everything below is interpretation, labeled as such. A reader who wants only the result can stop at the grid. The scope throughout is software-engineering tasks with deterministic graders, not general reasoning.

## The grid, read once

|  | cheap generator | frontier generator (Sonnet 4.5) |
|---|:--:|:--:|
| **standard SWE-Agent** | 27.7% <sup>a</sup> | 43.6% <sup>b</sup> |
| **methodeutic harness** | 93.1% <sup>c</sup> | 95.3% <sup>c</sup> |

Two numbers fall out of the margins. Hold the harness fixed and upgrade the model from a cheap open pair to a frontier pair, and the rate moves 2.2 points. Hold the model fixed at Sonnet 4.5 and swap the standard SWE-Agent scaffold for this harness, and it moves about fifty. The model tier is a small lever; the harness is a large one.

Read the grid the other way and the same shape returns as an interaction, with one honest caveat: the cheap-standard cell is a predecessor-lineage proxy (footnote a), so read the cheap column as indicative, not measured. Taken at face value, a frontier model beats a cheap one by roughly sixteen points under the standard scaffold and by two under this harness; the fully clean leg is the frontier column, 43.6 to 95.3. Either way the reading holds: the harness substitutes for model tier, a cheap model inside it nearly catches a frontier model, and most of the premium you would pay for better weights evaporates.

Two fences keep the "~fifty" honest. The 43.6 baseline runs Sonnet 4.5 with **thinking off** (SEAL's stated policy) while this harness runs it **thinking on** (Claude Code's interleaved thinking), so the lift bundles scaffold *and* thinking budget — and "the harness" also bundles generic agent-engineering (turn budget, tools, retries) it does not separate from the typed-inquiry structure; isolating those is the per-component ablation, and it is future work. What the magnitude *does* settle is bounded but real: bolting reasoning onto a fixed model is a single-digit lever on this bench (Sonnet 4.5 moves 77.2 → 82 on Verified with parallel test-time compute), so a ~50-point lift is not a reasoning artifact.

It also survives the strongest objection, *"your system just contains a strong model."* Grant it: induce the whole model contribution to the **stronger** of the two — GPT-5.5, which dominates Sonnet 4.5 and which the harness used only as a reasoning-off challenger. Its bare Pro score is ~58.6%; the single best model on the entire Pro board, Opus 4.7, is ~64.3%. Against either, the harness still adds **31–37 points**. The system leans on the *weaker* model for generation and barely taxes the stronger one, yet clears the stronger model's solo score by a wide margin. (Vendor/board scaffolds differ; treat these as bare-model anchors, not matched cells.)

One honest line on the fifty. The standard scaffold caps its turns, so that delta mixes the harness's structure with the compute it is allowed to spend. The grid supports "this harness against the standard one, same model," and stops short of "structure alone." A compute-matched bare arm would isolate structure, and that run is named in the future work.

## A dial with one axis

Capability today is sold as spend. Claude Code's `/effort` control (as of v2.1.68, May 2026) runs from "Faster" to "Smarter," and the "Smarter" end is the more-tokens end. Its top setting, `ultracode`, is defined as `xhigh + workflows`: maximum reasoning budget stacked with multi-agent fan-out. The `ultrathink` keyword allocates a 31,999-token thinking budget for a single turn, billed as output, roughly half a dollar at Sonnet rates, and the current default is maximum thinking with no keyword at all.

The dial offers a spend axis and no efficiency axis. You can turn the tokens up. There is no setting for doing the work with a leaner method. That absence is the whole point of the grid above, which restores the axis the product omits: method at fixed spend.

## The default is the testimony

Anthropic surely employs engineers who care about token efficiency. Efficiency is an engineering preference, though, and the shipped default is the institution's preference. The default ships at maximum. When the default thinking budget is also the ceiling, the organization has already said which preference won, and it said so in its own product rather than in any claim made about it.

The mechanism is not subtle. Usage pricing charges more when you spend more, and the default spends the most. You do not need a theory of intent to see where that points; you need arithmetic. The efficiency engineers lose, and they lose to the billing line.

More compute does genuinely help on hard instances, and this harness spends real compute too. Thinking having a budget is fine. The tell is that the budget defaults to maximum and the product exposes no lever for less. To the company's credit, they label the spend dial more plainly than most, and that plain label is the evidence; nothing here alleges anything they did not ship.

The default steers more than a slider. Most individual coders work on a subscription, in the interactive mode the product opens by default, and that mode is the token-heavy one: many turns, repeated context, a thinking budget that maxes out, no gate to stop early. The disciplined alternative is a structured harness, which is the thing the terms route to the meter and keep off the cheap path. So the efficient method is the one the mass market is steered away from, and the token-heavy default is the one it is steered toward, which is also the one that draws the most tokens. No one needs to be hooked on purpose for the structure to keep them there.

## Two ways to bill, and why the labs are quiet

A job shop bills for delivered parts and eats its own scrap, so it is driven to make less scrap. A contractor on cost-plus bills for work attempted, overruns included, so it is driven to economize on nothing: a failed run is still a billed run, and trimming it only shrinks the invoice. The two structures point their holders in opposite directions on one question, how little can this cost.

Per-token pricing is the cost-plus contract. Every attempt, retry, and dead-end thinking token bills at the rate of work that shipped, and the vendor carries no cost for the client's scrap. The product follows the contract: a thinking budget that defaults to maximum, a top tier of `xhigh + workflows`, a "Smarter" end that is the most expensive end. Under cost-plus that has a name. It is gold-plating: more billable work wearing the label of higher quality.

This is the honest answer to the obvious question, why an independent with a blog runs this measurement while the labs stay silent. Their engineers are better resourced than I am, so capability does not explain it. Gradient does. An independent has no token revenue, so failures cost him and only delivered solutions pay, which is the job-shop incentive, and that incentive is what drives you to find the harness that turns scrap into solutions and to publish the number. A lab on cost-plus has the opposite slope: a result reading "the same outcome for a tenth of the tokens" shrinks the invoice. They are not hiding it. They have little reason to look for it, and less to print it. Same problem, opposite slopes.

I will not allege intent, and not out of deference. Intent is the one thing a reader can dispute and the one thing I cannot prove, so asserting it gives the argument away. The effect needs no intent: you are billed for every failed attempt, and the default maximizes the failures you pay for. That is a cost-plus contract working exactly as cost-plus contracts do, and whether anyone meant it changes the invoice not at all.

The bill is not the only thing that scales with the wasted tokens. The compute behind a maximized default has a physical footprint in power and water and silicon, and that footprint does not care what drove it. Maximized for revenue or for a race to capability, the data center draws the same load. You do not have to settle the motive to count the cost.

## The job-shop unit cost

The honest unit cost of a result is the job-shop one: everything spent, divided by what was delivered.

```
cost per completed solution  =  total spend / solutions completed
                             =  spend per attempt / resolve rate
```

The first term is the model. The second is scrap. A system resolving 43.6% delivers one solution for every 2.3 attempts it bills, so at an identical per-attempt price it still costs 2.3 times as much per delivered solution as one resolving 95%. Low resolve is a high scrap rate, and the meter charges the client for the scrap.

| system | resolve | $ / completed solution | verifiable |
|---|--:|--:|:--:|
| *our harness · SWE-bench Pro public* | | | |
| open-weight · Composer 2.5 + Flash | 93.1% | ~$0.44 <sup>c</sup> | patches committed |
| frontier · Sonnet 4.5 + GPT-5.5 | 95.3% | ~$5.39 <sup>c</sup> | patches committed |
| *bare / minimal harness · cross-bench* | | | |
| GPT-5.5 · DeepSWE <sup>d</sup> | ~70% | ~$8.3 | no patches |
| GPT-5.4 · DeepSWE <sup>d</sup> | ~56% | ~$5.9 | no patches |
| Composer 2.5 · Hard-AA <sup>d</sup> | 47% | ~$0.15 | no patches |
| *gated SOTA* | | | |
| Claude Mythos Preview | 77.8% | **??** <sup>e</sup> | none |

The harness wins on both terms at once. It resolves high, so little is scrapped (about 1.05 attempts per delivered solution against the standard scaffold's 2.3), and it runs on a cheap model, so each attempt is cheap. The cheapness comes from the model, which supplies a low price per token; the resolve comes from the harness, which keeps the tokens from becoming scrap; and a low cost per delivered solution needs both.

One cell is blank, and the blank is the measurement. Our own rows you can run and re-grade from committed patches; the cross-bench rows are priced but ship none, so even their costs rest on the vendor's word; and Mythos cannot be priced at all, with no public API, no published rate, and no committed patches, so its cost per delivered solution is not computable from anything released. The most capable public number is the one you cannot weigh.

## Why a provider will not ship this

The labs stay quiet on the measurement for the reason above. They will not ship the method either, and for reasons just as structural.

Model providers do ship harnesses, and good ones: Claude Code, Cursor, Codex. The harness they will not ship is one carrying two of this one's properties.

It is token-efficient. It gets a frontier result from a cheap model by spending tokens well rather than spending more of them, so it lowers the billed tokens per delivered solution. A usage-billed provider that shipped it would be shipping the product that makes its customers buy less of what it sells. Their own harnesses move the other way, toward a maximized default, because that is the direction the billing line rewards.

It is model-agnostic. It ran Sonnet, GPT-5.5, Composer, and Flash without caring whose weights were inside, and the grid puts those weights at about two points. A provider's harness locks you to the provider's model; an agnostic one turns that model into a swappable part and invites a cheaper one, or a competitor's. Few vendors are eager to productize their own commoditization.

Efficiency cuts the bill, agnosticism cuts the lock-in, and both run against the revenue. There is also nowhere in the provider's economy to put such a harness. It bills two things: tokens through the API meter, and its own harness through the subscription. A method made of skills is neither. You cannot meter a method, since there is no token in it, and you cannot route the cheap subscription path through a third-party harness, since the terms restrict that to the house tool. Skills are not a billable surface, and the terms are where that becomes plain. And the one compliant rail a custom harness is left is the API meter, which at a full run's scale costs more than the subscription it is not allowed to use. The cheap path is reserved for the house tool; bring your own harness and you pay the meter. The provider captures value either way: run its harness and take the lock-in, or run yours and pay the metered premium. Whatever efficiency the harness wins, the routing rules take part of it back. So the harness that carries both properties comes most naturally from somewhere with no model to sell and no tokens to bill. It is a markdown file and a handful of skills, free to copy. The thing is not scarce. The incentive to distribute it is.

The demand is not hypothetical: as of May 2026, the most-starred software project on GitHub is an open, model-agnostic agent harness,<sup>f</sup> the fastest the platform has produced. The market reached for the category the incumbents will not ship. And that is the deeper bind: they optimized to meter tokens, and a layer that prices method instead has no meter they own.

## The dog that did not bark

Composer 2.5's published coding numbers all come from Cursor's own agent: Pro-Hard-AA at 47%, Multilingual at 79.8%, the closed CursorBench. A standardized-scaffold SWE-bench Pro number for Composer 2.5 is published nowhere we could find. Its predecessor lineage sits on the official board, and a separate board prices its base near 51%, yet the model's own neutral-scaffold figure is absent.

A neutral number would do one thing: separate the model from the harness. For a product whose value is the integrated agent, the bare-model figure is both off-message and likely unflattering, since a standardized-scaffold result closer to its base than to its headline would show the agent doing the lifting. That is the decomposition the grid performs. The absence is consistent with harness-amplified performance. I flag this as interpretation, not a finding; selective publication and product integration explain it on their own, with no one hiding anything. The effect is the same either way. The number that would let an outsider run the model-versus-harness split is the one number no vendor is moved to publish.

## What you can check

The public-board leader on Pro is Claude Mythos Preview at 77.8%, a model Anthropic has not made generally available: gated to the invite-only Project Glasswing, no public API, no committed patches. The cheap open pair in this harness clears it by about fifteen points, on a plan anyone can buy, and every patch is committed and re-gradable on the official grader.

That is the asymmetry, stated flat. The closed system cannot be weighed, priced, or rerun. The open one hands you the patches and asks you to re-grade them. The one move the giant cannot make is the one this repository makes by default.

Nothing here requires a villain. The engineers are able and well meant. The incentive is ordinary. The default is a reasonable-looking product decision. And the result is a structure that bills for failure, maximizes the failures it bills for, and draws the same load on the world whether or not anyone wished it. That is the uncomfortable part, and it is not that someone chose this. It is that no one had to.

---

<sub>**a** `kimi-k2-instruct`, official Scale board, SWE-Agent scaffold: a predecessor-lineage proxy for Composer 2.5's K2.5 base, which is unbenchmarked on this scaffold (a separate board shows K2.5 ≈ 51%) and whose own standard-scaffold Pro figure is unpublished. Treat the cheap-column harness delta as a bracket (~+42 to +65). **b** `claude-4-5-Sonnet` 43.60±3.60, official Scale board, SWE-Agent 250-turn — labs.scale.com/leaderboard/swe_bench_pro_public. **c** this repo: `runs/scored` 694/728 (95.3%), `runs/flash-composer` 678/728 (93.1%); /728 = 731 − 3 gold-patch defects; 0-byte capture counted as LOSS; the open-weight (`flash-composer`) run's WINs survive a stratified 60-WIN re-grade (60/60, 0 flips), the frontier run's a 6-WIN cross-language spot-check (6/6). Cost is the portable *economic* basis (every leg metered at public API rates): ~$5.14/instance frontier, ~$0.41 open-weight, divided by resolve for the $/completed-solution column above. The operator's actual cash was far lower because most legs ran on flat subscriptions, but that subsidy isn't reproducible by an API payer; the full derivation and the cash-vs-economic reconciliation are in [`COST_BASIS.md`](COST_BASIS.md). **d** DeepSWE and Hard-AA are harder sets than public Pro, so these $/solution figures conflate harness with set difficulty; reference points, not matched. $/solution = published $/task ÷ resolve. **e** No public API, no published rate, no committed patches; cost per completed solution is not computable from anything released. Mythos resolve from the benchlm aggregate board; deployment policy at red.anthropic.com/2026/mythos-preview and anthropic.com/glasswing. `/effort` and `ultrathink` behavior: Claude Code v2.1.68, May 2026. **f** OpenClaw: the most-starred software project on GitHub as of May 2026 (~375k stars), a point-in-time ranking that shifts; an open, model-agnostic agent; cited for category demand, not as an endorsement of the project.</sub>

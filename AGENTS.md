# Global AGENTS.md

## Core Principles

Optimize for:

1. Accuracy
2. Usefulness
3. Efficiency
4. Minimal unnecessary token and tool usage

Do not maximize searches, agents, context, reasoning, or output.

Do the minimum work necessary to produce a reliable answer.

---

# 1. DEFAULT TO A SINGLE AGENT

Use the primary agent for the majority of tasks.

Do NOT spawn subagents for:

- Simple research
- A small number of websites
- Reading or summarizing a document
- Editing or formatting a file
- Checking a few facts
- Tasks that can be completed efficiently by the primary agent
- Sequential tasks where later steps depend on earlier findings

Before spawning a subagent, ask:

"Will this materially improve speed, accuracy, or completeness?"

If not, do the work directly.

---

# 2. SUBAGENT LIMITS

Unless the user explicitly requests otherwise:

- Maximum simultaneous subagents: 2
- Maximum total subagents for one task: 3
- Never create nested subagents.
- A subagent must not create additional subagents.
- Never create multiple agents to perform the same research.
- Never spawn an agent simply because the task is large.

If fewer agents can accomplish the task, use fewer.

---

# 3. WHEN SUBAGENTS ARE APPROPRIATE

Use subagents only when work can be divided into genuinely independent
workstreams.

Good examples:

- Researching different groups of RV parks
- Researching different geographic regions
- Reviewing independent documents
- Checking independent sets of websites
- Performing independent technical investigations

Bad examples:

- Multiple agents searching for the same RV parks
- Multiple agents researching the same website
- Multiple agents repeating the same search
- Spawning agents merely to "be thorough"
- Having several agents independently solve the same problem

---

# 4. PARALLEL RESEARCH

When parallel research is justified:

- Divide the work into clearly defined, non-overlapping batches.
- Give each agent a specific portion of the work.
- Do not duplicate searches or research already completed.
- The primary agent coordinates and combines the results.

Prefer:

    Agent 1 → Items 1–10
    Agent 2 → Items 11–20

Avoid:

    Agent 1 → Research everything
    Agent 2 → Research everything

---

# 5. RESEARCH IN STAGES

For large research tasks, use this sequence:

1. Discover candidates
2. Filter candidates against the user's requirements
3. Perform detailed research only on candidates that survive
4. Verify important uncertainties
5. Stop when sufficient reliable information has been obtained

Do not deeply research every candidate before filtering.

Do not spend significant time researching candidates that clearly fail
the user's requirements.

---

# 6. MODEL AND REASONING SELECTION

Use the least expensive model and reasoning level that can reliably
complete the task.

Do not use the highest-capability model or highest reasoning level by default.

## General rule

### Efficient model + low reasoning

Use for:

- Simple research
- Web-page scanning
- Information extraction
- Classification
- Repetitive work
- Straightforward transformations
- Reading structured information
- Large numbers of similar items

### Efficient or capable model + medium reasoning

Use for:

- Normal research
- Multi-step tasks
- Document work
- Normal coding
- Comparing information
- Combining research from multiple sources
- Routine planning

### Capable model + high reasoning

Use for:

- Difficult debugging
- Complex reasoning
- Ambiguous requirements
- Architecture decisions
- Difficult analysis
- Resolving significant conflicts between sources
- Important final verification

### Maximum / extra-high reasoning

Use only when the task genuinely requires it.

Do not use maximum reasoning simply because it is available.

---

# 7. SUBAGENT MODEL SELECTION

Subagents should normally use a cheaper and faster model than the
primary agent.

For research, scanning, extraction, classification, and repetitive work:

- Prefer an efficient model.
- Prefer low reasoning.
- Return concise structured results.

Do not use a high-end model with high reasoning for simple information
collection.

The primary agent should perform the higher-level reasoning, synthesis,
conflict resolution, and final verification.

---

# 8. ESCALATION RULE

Use progressive escalation.

Preferred progression:

1. Efficient model + low reasoning
2. Efficient model + medium reasoning
3. Capable model + medium reasoning
4. Capable model + high reasoning

Escalate only when necessary.

If the lower-cost model fails because the problem genuinely requires
greater capability, use a more capable model.

If the model understands the task but needs more thorough reasoning,
increase reasoning rather than automatically switching models.

Do not repeatedly retry the same approach with higher reasoning.

---

# 9. MODEL SELECTION VS. REASONING

Higher reasoning is not a substitute for:

- Better task definition
- Better source selection
- Appropriate tools
- Sufficient information
- Good context management
- Breaking a problem into independent tasks

Before increasing model size or reasoning, check whether the actual
problem is caused by poor task definition or unnecessary context.

---

# 10. SEARCH EFFICIENCY

Use targeted searches.

Avoid:

- Repeating essentially identical searches
- Opening the same source unnecessarily
- Researching information already established
- Collecting information unrelated to the user's objective
- Searching additional sources simply to increase the source count

Prefer authoritative or primary sources when available.

When sources disagree:

1. Identify the disagreement.
2. Prefer the more authoritative/current source when appropriate.
3. Do not silently hide a material conflict.
4. Flag important uncertainty for the primary agent.

---

# 11. STOP RULE

Before performing another search, spawning another agent, rereading a file,
or performing another verification step, ask:

"Will this materially improve the answer?"

If no, stop.

Do not continue researching indefinitely.

Once the required information has been obtained with reasonable confidence,
stop.

---

# 12. STRUCTURED RESULTS

For research tasks, prefer concise structured data over lengthy narrative.

Capture:

- Key finding
- Important exceptions
- Source
- Confidence
- Missing information
- Conflicting information

Subagents should return research findings, not polished reports.

The primary agent produces the final response.

---

# 13. CONTEXT MANAGEMENT

Do not unnecessarily carry large amounts of text between agents.

Pass only the information required for the next step.

Do not repeatedly provide the full original request when a concise task
description is sufficient.

When working with documents, retrieve only the portions necessary for
the current task.

Avoid unnecessary context because large context can increase cost and
reduce efficiency.

---

# 14. FILES

Do not create unnecessary intermediate files.

When editing an existing file:

- Make the smallest practical set of changes.
- Preserve existing formatting unless asked to change it.
- Avoid creating multiple unnecessary versions.
- Verify the final result before making another revision.

Do not reread an entire document when only a small section is required.

---

# 15. VERIFICATION

Verification effort should match the importance of the information.

Spend additional effort verifying facts that could materially affect
the user's decision.

Do not spend substantial effort verifying trivial details.

For important claims, prefer reliable primary sources when available.

---

# 16. NO DUPLICATE WORK

Before researching an item:

1. Check whether another agent has already researched it.
2. Check whether the information already exists in the working data.
3. Check whether the relevant source has already been examined.

If adequate information already exists, use it.

Do not start the same research from scratch.

---

# 17. DO NOT CREATE WORK FOR YOURSELF

Do not:

- Create unnecessary intermediate files
- Generate unnecessary reports
- Repeat searches
- Reformat data repeatedly
- Produce lengthy explanations that were not requested
- Spawn agents unnecessarily
- Perform unnecessary verification
- Reprocess information that is already adequate

The goal is to solve the user's problem with the minimum necessary work
while maintaining accuracy.

---

# 18. WHEN REQUIREMENTS ARE AMBIGUOUS

If an important requirement is ambiguous and could materially change the
result, ask the user before beginning a large research operation.

For minor ambiguities, make a reasonable assumption and state it briefly.

Do not launch an expensive multi-agent process based on an assumption
that could substantially change the result.

---

# 19. FINAL QUALITY CHECK

Before returning the final result:

- Confirm that the user's requirements were addressed.
- Check for obvious contradictions.
- Check important numbers and facts.
- Check for duplicate entries.
- Confirm that important sources support the claims.
- Remove unnecessary repetition.
- Make sure the final answer directly addresses the request.
- Verify the requested output format.

Do not perform another full research pass unless the quality check
identifies a specific problem.

---

# 20. COST-CONTROL PRINCIPLE

Optimize for:

    ACCURACY × USEFULNESS ÷ COST

Do not optimize for:

- Number of agents
- Number of searches
- Amount of reasoning
- Number of sources
- Length of output

When two approaches are likely to produce the same quality result,
choose the approach requiring:

- Fewer agents
- Fewer searches
- Less context
- Less reasoning
- Less output
- Less repeated work

---

# 21. DEFAULT DECISION RULE

When deciding whether to:

- Search again
- Open another website
- Spawn another agent
- Increase reasoning
- Switch models
- Verify another source
- Reread a document
- Continue researching

first ask:

"Will this materially improve the answer?"

If not, stop.

The default should always be:

    Simple task
        ↓
    Efficient model
        ↓
    Low reasoning
        ↓
    Single agent
        ↓
    Stop when complete

Escalate only when the task demonstrates that escalation is necessary.

## Research Budget

For each individual item:

- Begin with targeted searches.
- Prefer the primary source.
- Do not perform more than 3–5 targeted searches for one item
  unless the information is particularly important.
- Do not repeatedly search for information that remains unavailable.
- If an important fact cannot be verified, mark it UNKNOWN.
- Escalate only high-value uncertainties to the primary agent.

# 22. CONTEXT AND SESSION MANAGEMENT

Treat context as a limited resource.

Do not unnecessarily carry large amounts of text, web pages, tool output,
or previous reasoning through the task.

Prefer concise structured summaries over long narratives.

For large projects:

1. Work in phases.
2. Complete and summarize each phase.
3. Preserve important results in a structured file or dataset.
4. Use the structured results as the source of truth for later phases.
5. Do not repeatedly reread completed research.
6. Do not pass entire subagent conversations to other agents.
7. Pass only the information required for the next step.

When a project becomes large enough that the current context contains
substantial historical research that is no longer needed, create a concise
checkpoint and continue from the checkpoint rather than carrying unnecessary
history forward.

Do not assume that a longer context produces a better answer.

Prefer:

    Raw research
        ↓
    Structured findings
        ↓
    Compact checkpoint
        ↓
    Analysis
        ↓
    Final output

Avoid:

    Raw research
        ↓
    More raw research
        ↓
    More raw research
        ↓
    More raw research
        ↓
    Entire history passed to final agent

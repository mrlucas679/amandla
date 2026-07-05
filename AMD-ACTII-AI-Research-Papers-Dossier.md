# AMD ACT II - AI Research Papers Dossier

> Living research file for AMD ACT II. This is not a generic "read every AI paper" dump. It is a
> project-filtered knowledge base: what each paper teaches us about building a reliable multi-agent
> operations OS for SA FMCG/retail, with evidence contracts, critic review, HITL, RAG/memory,
> deterministic simulation, and AMD MI300X/vLLM inference.

## How To Navigate This File

- Start with **Project Lens** to understand how papers are judged for usefulness.
- Each numbered section maps to the user's research list.
- Each section has:
  - **Why This Category Matters**
  - **Selected Papers**
  - **Project Takeaways**
  - **Build/Design Decisions**
  - **What We Are Not Using Yet**
- The file is meant to grow. Completed sections are listed below.

## Coverage Tracker

| # | Research Area | Status | Project Relevance |
|---|---|---|---|
| 1 | Foundations of Deep Learning | Complete | Indirect but important: scaling, trainability, efficiency, transfer, GPU inflection |
| 2 | Transformer and Attention | Complete | Direct: LLM backbone, context, inference cost, prompt/runtime design |
| 3 | Language Models | Complete | Direct: model choice, open models, small vs mid tier |
| 4 | Fine-Tuning and Adaptation | Complete | Roadmap/direct: LoRA/QLoRA, domain adaptation, cost |
| 5 | Reinforcement Learning and Preference Optimization | Complete | Indirect/direct: RLHF/DPO/GRPO for agent alignment and action ranking |
| 6 | Multi-Agent Systems | Complete | Direct: orchestrator, critic, agent roles |
| 7 | Reasoning Models | Complete | Direct: evidence, critic, self-refinement, planning |
| 8 | RAG | Complete | Direct: memory/RAG, grounded decisions |
| 9 | Vector Databases and Search | Complete | Direct: pgvector, HNSW/IVFFlat, retrieval design |
| 10 | GPU Training and Parallelism | Complete | Direct/roadmap: MI300X story, vLLM, scaling |
| 11 | Model Compression | Complete | Direct: quantization, latency/cost |
| 12 | Multimodal AI | Complete | Roadmap: scanner, images, documents |
| 13 | Computer Vision | Complete | Roadmap: scanner, shelf, product verification |
| 14 | Image Generation | Complete | Low/direct only for cover/demo assets, not core product |
| 15 | Audio and Speech | Complete | Roadmap: voice interface/transcription |
| 16 | MLOps and Model Management | Complete | Direct: model registry, evals, deployment |
| 17 | AI Safety and Alignment | Complete | Direct: HITL, critic, grounded output |
| 18 | Memory Systems | Complete | Direct: learned patterns, decision records |
| 19 | Knowledge Graphs | Complete | Roadmap: Detective/root cause, GraphRAG |
| 20 | Enterprise AI Systems | Complete | Direct: governance, workflow, routing |
| 21 | Synthetic Data | Complete | Direct: seeded data, eval fixtures |
| 22 | Evaluation and Benchmarks | Complete | Direct: golden scenario, metrics |

## Project Lens

When a paper is included, it must help at least one of these:

1. Make the 5-agent cascade more reliable.
2. Improve evidence, critic review, HITL, or action routing.
3. Improve RAG/memory over events, decisions, product state, and learned patterns.
4. Improve open-model inference on AMD MI300X/vLLM or Fireworks fallback.
5. Improve latency, cost, eval, observability, or demo determinism.
6. Explain roadmap features without destabilizing the MVP.

Use `get-shit-done` here: if a paper is famous but does not improve the demo, implementation, or
roadmap narrative, it gets a short note, not a long essay.

---

# 1. Foundations Of Deep Learning

## Why This Category Matters

Most of these papers do not directly tell us how to build the AMD ACT II app. The app is LLM-first,
not a vision model training system. Still, this category teaches foundational engineering lessons:

- **Learning needs feedback:** Backprop is the ancestor of our own validate-then-retry, critic, and
  eval loop mindset.
- **Data + compute changes what is possible:** AlexNet matters because it made GPUs and scale central
  to modern AI. That connects directly to our AMD MI300X story.
- **Depth needs information-flow design:** ResNet/DenseNet teach that deep systems fail without
  good pathways for signal and gradients. Our multi-agent architecture has the same lesson: compact
  evidence objects, trace ids, and critic feedback are information highways.
- **Efficiency is a first-class design goal:** EfficientNet teaches principled scaling under resource
  constraints. Our version is "right-size model, context, tools, and GPU hours."
- **Transfer beats training everything from scratch:** LeNet/AlexNet/VGG/ViT all reinforce a project
  rule: use strong pretrained models and adapt prompts/tools/evals, rather than training from zero.

## Selected Papers And Systems

### 1.1 Perceptron - Rosenblatt (1958)

**Primary source:** Rosenblatt, "The perceptron: a probabilistic model for information storage and
organization in the brain," Psychological Review, 1958. PubMed page:
https://pubmed.ncbi.nlm.nih.gov/13602029/

**Core idea:** A simple trainable classifier learns decision boundaries from examples.

**Why it matters to us:** Mostly historical. It introduces the idea that behavior can emerge from
learned weights rather than hand-written rules. For AMD ACT II, it is useful as a reminder that
learned systems are constrained by representation and data quality. A perceptron cannot solve a
nonlinear problem without the right representation; our agents cannot reason correctly without the
right event schema, product state, and evidence.

**Project takeaway:**
- Do not expect "AI" to overcome bad representation. The Event/Evidence/Decision contracts are not
  bureaucracy; they are the representation that makes reasoning possible.

**MVP action:** No implementation action. Keep as background.

### 1.2 Backpropagation - Rumelhart, Hinton, Williams (1986)

**Primary source:** Rumelhart, Hinton, Williams, "Learning representations by back-propagating
errors," Nature, 1986. Nature page:
https://www.nature.com/articles/323533a0

**Core idea:** Repeatedly adjust network weights to reduce the difference between actual and desired
outputs. The important system lesson is closed-loop correction from error signals.

**Why it matters to us:** We are not training neural nets in the MVP, but the same loop appears in
our architecture:

- Agent emits structured output.
- Pydantic validates it.
- On failure, one retry feeds the validation error back.
- Critic reviews evidence and downgrades/rejects unsupported claims.
- Golden scenario tests give a system-level error signal.
- Decision outcomes become the substrate for visible learning.

**Project takeaway:**
- Treat every AI call as part of a feedback loop, not a one-shot oracle.
- The validation error, critic verdict, and golden-scenario failure are our "error gradients."
- This supports the existing design choice: structured output -> validate -> retry once -> safe default.

**MVP action:**
- Keep `guarded_parse`.
- Keep Critic as a visible reviewer.
- Keep eval logs and traces so failures produce actionable feedback.

### 1.3 LeNet-5 - LeCun, Bottou, Bengio, Haffner (1998)

**Primary sources:**
- IEEE page: https://ieeexplore.ieee.org/document/726791
- PDF mirror from Stanford course materials:
  https://vision.stanford.edu/cs598_spring07/papers/Lecun98.pdf

**Core idea:** End-to-end gradient-based training can replace hand-engineered feature pipelines for
document recognition.

**Why it matters to us:** The biggest relevant lesson is not the convolution details. It is the
pipeline lesson: useful AI systems still combine multiple modules. LeNet-5 was part of a real document
recognition system, not just a standalone classifier.

AMD ACT II is also a system, not one model:

- CSV/scanner ingestion.
- Event normalization.
- Agent fan-out.
- Evidence contracts.
- Critic review.
- Simulation tool.
- Action router.
- HITL.
- Decision log.
- UI trace.

**Project takeaway:**
- Judge the system end-to-end, not just model quality.
- The scanner should always have a deterministic "Simulate scan" fallback, because system reliability
  beats live-demo purity.

**MVP action:**
- Do not overbuild computer vision scanning now.
- Use the browser scanner lightly and make "Simulate scan" the reliable trigger.

### 1.4 AlexNet - Krizhevsky, Sutskever, Hinton (2012)

**Primary source:** "ImageNet Classification with Deep Convolutional Neural Networks," NeurIPS 2012:
https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks

**Core idea:** A large CNN trained on ImageNet using GPUs dramatically improved image classification.
The paper's system-level importance is the combination of data scale, GPU compute, architecture, and
regularization.

**Why it matters to us:** AlexNet is one of the clearest historical proofs that GPU acceleration is
not a footnote. It changes the feasible product envelope. For our hackathon:

- The AMD MI300X/vLLM path should be visible, not hidden.
- We should show a concrete endpoint, token/sec number, or trace/cost number.
- "Application of Technology" is not satisfied by a vague claim that we used AI.

**Project takeaway:**
- Our AMD story should be as concrete as AlexNet's GPU story: open model, served by vLLM/ROCm on MI300X,
  same OpenAI-compatible client as Fireworks, measured in trace/tokens/latency.

**MVP action:**
- Record one MI300X run.
- Capture a tokens/sec or latency figure.
- Put it in README, slide deck, and demo narration.

### 1.5 VGG - Simonyan, Zisserman (2014/2015)

**Primary sources:**
- arXiv: https://arxiv.org/abs/1409.1556
- Oxford VGG page: https://www.robots.ox.ac.uk/~vgg/publications/2015/Simonyan15/

**Core idea:** Depth matters; repeated small 3x3 filters produced strong image representations and
transferable features.

**Why it matters to us:** VGG is less directly useful than ResNet/EfficientNet for this project, but
it gives a transferable design lesson: simple repeated blocks can scale surprisingly well when the
interface is clean.

In AMD ACT II terms:

- One `EvidenceObject` shape across agents is our repeated block.
- One inference client across Fireworks/vLLM is our repeated block.
- One BFF contract across UI zones is our repeated block.

**Project takeaway:**
- Prefer one repeated, well-tested pattern over custom per-agent machinery.

**MVP action:**
- Keep all agents on the same runner and evidence contract.
- Do not create bespoke agent output formats.

### 1.6 ResNet - He, Zhang, Ren, Sun (2015)

**Primary source:** "Deep Residual Learning for Image Recognition," arXiv:
https://arxiv.org/abs/1512.03385

**Core idea:** Residual connections make very deep networks easier to optimize by letting layers learn
residual functions relative to their inputs.

**Why it matters to us:** ResNet is one of the most important architecture lessons for any deep system:
information needs reliable pathways around complex transformations.

Our multi-agent equivalent:

- Do not pass raw, bloated chat transcripts upward.
- Pass compact evidence records upward.
- Preserve source refs and correlation ids so downstream layers can audit the original facts.
- Let the Critic and Executive operate on evidence, not hidden agent thoughts.

**Project takeaway:**
- `EvidenceObject` is the residual connection of the agent OS: it preserves the important signal
  through a deep cascade.
- Trace ids are the skip path that lets us debug and explain the cascade.

**MVP action:**
- Keep evidence compact and auditable.
- Preserve `correlation_id`, `caused_by`, and `SourceRef` through every stage.
- Add UI trace panel so users see this information flow.

### 1.7 DenseNet - Huang, Liu, van der Maaten, Weinberger (2016)

**Primary source:** "Densely Connected Convolutional Networks," arXiv:
https://arxiv.org/abs/1608.06993

**Core idea:** Connect each layer to all subsequent layers to improve feature reuse, gradient flow,
and parameter efficiency.

**Why it matters to us:** DenseNet is a useful warning and inspiration. Rich connectivity improves
information reuse, but uncontrolled connectivity can explode complexity.

For AMD ACT II:

- Agents should not all talk to all agents.
- The orchestrator should selectively route.
- Shared memory/RAG should provide reusable facts.
- Executive should see compact outputs, not everything.

**Project takeaway:**
- Use controlled information reuse: shared product state, learned patterns, and evidence records.
- Avoid N-by-N agent chatter.

**MVP action:**
- Keep selective firing.
- Keep one shared memory context per SKU.
- Do not implement debate between every agent.

### 1.8 EfficientNet - Tan, Le (2019)

**Primary source:** "EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks," arXiv:
https://arxiv.org/abs/1905.11946

**Core idea:** Scaling a model is better when depth, width, and input resolution are balanced with a
compound coefficient, rather than scaling one dimension blindly.

**Why it matters to us:** EfficientNet is highly relevant as a scaling philosophy. Our app has its own
scaling axes:

- Number of agents.
- Number of tools loaded per agent.
- Context length.
- Model size.
- Number of LLM calls.
- Retrieval depth.
- GPU runtime hours.

Blindly increasing any one of these can hurt reliability or cost. The project already follows this
principle by building the 5-agent spine instead of all 14 full agents.

**Project takeaway:**
- Scale the system in balanced dimensions: right-sized model, right-sized context, right-sized tool
  set, right-sized agent count.
- Do not use a bigger model to compensate for weak data contracts.

**MVP action:**
- Keep each agent prompt in the 16K-24K reliable zone.
- Keep tools deferred and top-k.
- Use one 7B-8B model for routine agents; optionally route Executive/Critic to a larger model only
  if it improves the demo.

### 1.9 Vision Transformer - Dosovitskiy et al. (2020/2021)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2010.11929
- OpenReview: https://openreview.net/forum?id=YicbFdNTTy

**Core idea:** Images can be represented as sequences of patches and processed by a standard
Transformer, achieving strong results when pretrained at scale.

**Why it matters to us:** ViT belongs partly in the next category too, but it is useful here as the
bridge from CNN foundations to transformer-era foundation models. The direct MVP is not image-heavy,
but the roadmap includes scanner, shelf, product, and document inputs.

**Project takeaway:**
- Treat modality as a representation problem. An image, event log, decision table, or product record
  can become a sequence of tokens/facts if the interface is clean.
- Pretraining plus transfer is the normal path. Do not train vision models from scratch.

**MVP action:**
- For the hackathon, keep scanning simple.
- For roadmap, use pretrained multimodal/vision encoders or hosted models if product images become
  important.

## Project Takeaways From Category 1

### A. The Evidence Contract Is The Key Representation

The perceptron and backprop history both say the same thing: learning only works through the right
representation and feedback. For AMD ACT II, `Event`, `EvidenceObject`, and `Decision` are the
representations that make the agent OS credible.

### B. GPU Usage Must Be Concrete

AlexNet's lasting lesson is "data plus GPU compute changed what worked." For AMD ACT II, do not hide
the AMD compute. Show:

- vLLM endpoint.
- model name.
- MI300X/ROCm path.
- token/sec or latency.
- trace/cost numbers.

### C. Deep Systems Need Skip Paths

ResNet/DenseNet map directly to our trace and evidence strategy. The cascade can be deep only if
facts move through it cleanly:

- `SourceRef`
- `correlation_id`
- `caused_by`
- compact `supporting_data`
- visible trace panel

### D. Balanced Scaling Beats Bigger Everything

EfficientNet is the strongest category-1 paper for current architecture discipline. It supports:

- 5-agent spine, not 14 full agents.
- deferred tools, not all tools loaded.
- compact RAG facts, not raw rows.
- small routine model, optional bigger Executive/Critic.
- Fireworks fallback, MI300X proof path.

### E. End-To-End Systems Beat Isolated Models

LeNet and AlexNet both mattered as systems. AMD ACT II should be evaluated as a full product loop:

ingest -> reason -> verify -> route -> approve -> log -> learn -> show in UI.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep 5-agent spine full, stub rest | EfficientNet | Balanced scaling under constraints |
| Use one evidence contract everywhere | VGG, ResNet | Repeated clean block, information preservation |
| Preserve trace/provenance through cascade | ResNet, DenseNet | Deep systems need reliable signal flow |
| Show MI300X/vLLM concretely | AlexNet | GPU compute is part of the technology story |
| Use pretrained open models, not training from scratch | LeNet, AlexNet, ViT | Transfer is practical; from-scratch training is not MVP |
| Keep scanner simple with simulate fallback | LeNet, ViT | Vision can be roadmap; system reliability matters now |
| Validate/retry/critic/eval loop | Backprop | Correction signals make AI systems improve |

## What We Are Not Using Yet

- No custom CNN training.
- No from-scratch vision model.
- No large-scale image pipeline.
- No all-agent dense communication graph.
- No bigger-model-by-default strategy.

These are roadmap or background ideas, not MVP work.

## Category 1 Source List

- Rosenblatt, "The perceptron: a probabilistic model for information storage and organization in
  the brain" (1958): https://pubmed.ncbi.nlm.nih.gov/13602029/
- Rumelhart, Hinton, Williams, "Learning representations by back-propagating errors" (1986):
  https://www.nature.com/articles/323533a0
- LeCun, Bottou, Bengio, Haffner, "Gradient-Based Learning Applied to Document Recognition" (1998):
  https://ieeexplore.ieee.org/document/726791
- Krizhevsky, Sutskever, Hinton, "ImageNet Classification with Deep Convolutional Neural Networks"
  (2012): https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks
- Simonyan, Zisserman, "Very Deep Convolutional Networks for Large-Scale Image Recognition" (2014):
  https://arxiv.org/abs/1409.1556
- He, Zhang, Ren, Sun, "Deep Residual Learning for Image Recognition" (2015):
  https://arxiv.org/abs/1512.03385
- Huang, Liu, van der Maaten, Weinberger, "Densely Connected Convolutional Networks" (2016):
  https://arxiv.org/abs/1608.06993
- Tan, Le, "EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks" (2019):
  https://arxiv.org/abs/1905.11946
- Dosovitskiy et al., "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale"
  (2020/2021): https://arxiv.org/abs/2010.11929

---

# 2. Transformer And Attention

## Why This Category Matters

This is one of the most directly useful categories for AMD ACT II. The project is not training a
new foundation model, but it depends on Transformer LLMs for every intelligent step in the cascade.
Attention research tells us what is expensive, what is fragile, and where product architecture must
protect the model from bad context.

The key lesson is simple: **attention is not magic memory.** It is a compute and memory budget. The
app should spend that budget on compact evidence, source refs, business thresholds, and current
state, not raw logs or giant transcripts.

For AMD ACT II, this category informs:

- Agent context assembly.
- RAG/memory design.
- vLLM/MI300X inference path.
- Fireworks fallback parity.
- Model selection for latency and cost.
- Why the 5-agent spine is better than "turn on every agent."
- Why trace, source refs, and evidence contracts matter more than long prompts.

## Selected Papers And Systems

### 2.1 Attention Is All You Need - Vaswani et al. (2017)

**Primary sources:**
- arXiv: https://arxiv.org/abs/1706.03762
- NeurIPS page: https://papers.nips.cc/paper/7181-attention-is-all-you-need

**Core idea:** The Transformer replaces recurrence/convolution with self-attention, multi-head
attention, positional information, and parallel computation over sequence tokens.

**Why it matters to us:** This is the base architecture behind the LLMs we will use. The product
lesson is that the model reasons over whatever sequence we give it. If we pass noisy context, stale
rows, or ungrounded summaries, attention happily spends compute on the wrong facts.

In AMD ACT II, the "tokens" are not only words. They are business facts:

- SKU.
- store.
- inventory count.
- expiry date.
- sell-through.
- markdown option.
- simulated ZAR impact.
- source refs.
- critic verdict.
- HITL policy.

**Project takeaway:**
- The context assembler is a first-class system component. It decides what facts enter the model's
  attention field.
- Evidence should be compact, structured, and source-linked.
- Do not use the LLM as a database. Use Postgres/pgvector for memory and pass only the relevant facts.

**MVP action:**
- Keep prompts evidence-first.
- Keep agent context inside the reliable 16K-24K target.
- Put exact `SourceRef`, `correlation_id`, SKU, store, and threshold facts near the top of the prompt.

### 2.2 Transformer-XL - Dai et al. (2019)

**Primary sources:**
- arXiv: https://arxiv.org/abs/1901.02860
- ACL Anthology PDF: https://aclanthology.org/P19-1285.pdf

**Core idea:** Transformer-XL extends language modeling beyond fixed windows using segment-level
recurrence and positional encoding designed to preserve temporal coherence.

**Why it matters to us:** Our app has temporal state: yesterday's scan, last week's markdown,
historic sell-through, learned thresholds, prior decisions, and decision outcomes. Transformer-XL
reinforces the idea that history should be carried forward deliberately, not reloaded as a giant
blob.

**Project takeaway:**
- Memory should be summarized into reusable state, not replayed as raw history.
- Decision logs become useful when converted into compact learned patterns.
- Temporal coherence belongs in the memory layer and event chain, not only in a long prompt.

**MVP action:**
- Pass a compact per-SKU memory block into relevant agents.
- Preserve `caused_by` and `correlation_id` across events and decisions.
- Keep visible learning as an actual state update, not a narrative claim.

### 2.3 Reformer - Kitaev, Kaiser, Levskaya (2020)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2001.04451
- OpenReview: https://openreview.net/forum?id=rkgNKkHtvB

**Core idea:** Reformer reduces Transformer memory/cost using locality-sensitive hashing attention
and reversible residual layers.

**Why it matters to us:** Reformer is useful less as a model choice and more as a warning. Efficient
attention often introduces approximation, implementation complexity, or quality tradeoffs. For a
hackathon product, the right move is not to invent an attention variant. The right move is to choose
well-supported open models and a strong serving runtime.

**Project takeaway:**
- Do not build custom attention or exotic serving code in the MVP.
- Optimize at the context, routing, model-selection, and serving-runtime layers.

**MVP action:**
- Use vLLM/Fireworks instead of custom inference.
- Avoid experimental models unless they are already supported by the serving stack.

### 2.4 Longformer - Beltagy, Peters, Cohan (2020)

**Primary source:** arXiv: https://arxiv.org/abs/2004.05150

**Core idea:** Longformer combines local sliding-window attention with task-motivated global
attention to handle long documents more efficiently.

**Why it matters to us:** Longformer maps cleanly to product context design. Most facts should be
local to the current SKU/store/event. A few facts should act as global anchors: tenant, store, SKU,
risk policy, current objective, threshold, source refs, and approval rules.

**Project takeaway:**
- Treat prompts like structured attention layouts: local context plus global anchors.
- The most important facts must be repeated in stable positions, not buried deep in retrieved text.

**MVP action:**
- Context builder should always include a small "global facts" block.
- Retrieved facts should be top-k and local to the current decision.

### 2.5 BigBird - Zaheer et al. (2020)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2007.14062
- NeurIPS PDF: https://proceedings.neurips.cc/paper_files/paper/2020/file/c8512d142a2d849725f31a9a7a361ab9-Paper.pdf

**Core idea:** BigBird uses sparse attention with local, random, and global tokens, reducing
quadratic attention cost while preserving important expressivity properties.

**Why it matters to us:** The useful design idea is the global token. In our app, "global tokens" are
business invariants and constraints that every agent must see:

- Never fabricate facts.
- Use ZAR money exactly.
- Respect HITL for high risk.
- Show source refs.
- Prefer monitor when evidence is weak.
- Preserve trace ids.

**Project takeaway:**
- Product policies should be always-present global context, not optional prompt decoration.
- Agents should receive the same core operating constraints even when their domain facts differ.

**MVP action:**
- Create one shared prompt contract block for agent rules and evidence formatting.
- Do not duplicate inconsistent policy wording across agents.

### 2.6 Linformer And Performer - Wang et al. (2020), Choromanski et al. (2020)

**Primary sources:**
- Linformer arXiv: https://arxiv.org/abs/2006.04768
- Performer arXiv: https://arxiv.org/abs/2009.14794

**Core idea:** Both explore linear-time alternatives or approximations to standard attention.
Linformer uses low-rank structure; Performer uses random feature methods to approximate softmax
attention.

**Why it matters to us:** These papers reinforce that sequence length has real cost. They are not
direct MVP implementation choices because AMD ACT II will use existing open LLMs through compatible
serving systems.

**Project takeaway:**
- Long context should be earned by relevance, not treated as free.
- Efficient attention is a model/runtime concern; product code should focus on smaller, better
  context.

**MVP action:**
- Do not stuff all POS rows, inventory rows, or decision logs into prompts.
- Use retrieval and summaries before the LLM call.

### 2.7 FlashAttention - Dao et al. (2022)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2205.14135
- OpenReview PDF: https://openreview.net/pdf?id=H4DqfPSibmx

**Core idea:** FlashAttention computes exact attention with an IO-aware algorithm that reduces GPU
memory reads/writes between high-bandwidth memory and on-chip SRAM.

**Why it matters to us:** This is central to the AMD story. The important point is not only "attention
is O(n^2)." The real bottleneck can be memory traffic. For MI300X/vLLM, performance claims should be
measured on the runtime we actually use.

**Project takeaway:**
- Application-of-technology scoring improves when we show concrete GPU inference behavior, not vague
  AI wording.
- Measure token latency and throughput for the cascade or one representative agent call.

**MVP action:**
- Record model name, context length, output tokens, latency, and tokens/sec for the MI300X run.
- Mention optimized attention/runtime only when actually used by the serving path.

### 2.8 FlashAttention-2 - Dao (2023)

**Primary source:** arXiv: https://arxiv.org/abs/2307.08691

**Core idea:** FlashAttention-2 improves parallelism and work partitioning so attention kernels use
GPU compute more effectively.

**Why it matters to us:** It teaches a deeper engineering rule: asymptotic complexity is not enough.
GPU utilization, memory layout, kernel support, batching, and serving scheduler behavior all matter.

**Project takeaway:**
- Do not assume a model is fast because a paper says the architecture is efficient.
- Benchmark the actual model, actual context length, actual serving backend, and actual hardware path.

**MVP action:**
- Keep a simple benchmark note in the submission package.
- Compare Fireworks fallback latency with vLLM/MI300X if both are available.

### 2.9 Multi-Query Attention - Shazeer (2019)

**Primary source:** arXiv: https://arxiv.org/abs/1911.02150

**Core idea:** Share key/value heads across attention heads to reduce KV tensor size and memory
bandwidth during incremental decoding.

**Why it matters to us:** AMD ACT II will generate many short-to-medium structured outputs across
multiple agents. Decoder inference speed and KV-cache memory directly affect cost, latency, and how
many agent calls can run during the demo.

**Project takeaway:**
- Model architecture matters for serving, not just leaderboard quality.
- KV-cache cost compounds when several agents run in one cascade.

**MVP action:**
- Prefer model families with efficient decoding characteristics when quality is acceptable.
- Keep agent fan-out selective.

### 2.10 Grouped-Query Attention - Ainslie et al. (2023)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2305.13245
- ACL Anthology: https://aclanthology.org/2023.emnlp-main.298/

**Core idea:** GQA sits between multi-head attention and multi-query attention, aiming for quality
close to full multi-head attention with speed closer to multi-query attention.

**Why it matters to us:** GQA is directly relevant to open-model selection because many modern
serving-friendly LLMs use grouped query attention. It gives a practical reason to check architecture
details before choosing the demo model.

**Project takeaway:**
- Model selection should include serving architecture: context length, GQA/MQA, quantization support,
  vLLM support, ROCm support, and structured-output quality.

**MVP action:**
- Keep a `model-card.md` note for the selected model: architecture, context, quantization, GQA/MQA,
  vLLM/ROCm status, and measured latency.

### 2.11 RoPE - Su et al. (2021)

**Primary source:** arXiv: https://arxiv.org/abs/2104.09864

**Core idea:** Rotary Position Embedding applies position-dependent rotations to query/key vectors,
encoding relative position information in the attention computation.

**Why it matters to us:** RoPE is used in many modern open LLM families. The product lesson is that
position matters: facts near the front, facts near each other, and facts repeated consistently can
matter. Long-context claims do not remove the need for disciplined prompt layout.

**Project takeaway:**
- Context ordering is part of product reliability.
- Put instructions, business invariants, current event, and evidence before optional background.

**MVP action:**
- Do not rely on a model to find buried constraints.
- Keep output schema and source-ref rules near the agent task.

### 2.12 ALiBi - Press, Smith, Lewis (2021)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2108.12409
- OpenReview: https://openreview.net/forum?id=R8sQPpGCv0

**Core idea:** ALiBi adds distance-based attention biases that help models extrapolate to longer
sequences than those seen during training.

**Why it matters to us:** This supports a conservative rule: a model's context window is not the same
as reliable reasoning over every token in that window. We should design the app so important context
is small and relevant even if the selected model supports long windows.

**Project takeaway:**
- Long context is a fallback capability, not a design excuse.
- Reliable business reasoning should come from retrieval, summarization, and exact contracts.

**MVP action:**
- Keep the 16K-24K reliable-context target.
- Use "more context" only when it improves the golden scenario or real evals.

### 2.13 S4, Hyena, And Mamba - Gu et al. (2021), Poli et al. (2023), Gu and Dao (2023)

**Primary sources:**
- S4 arXiv: https://arxiv.org/abs/2111.00396
- Hyena arXiv: https://arxiv.org/abs/2302.10866
- Mamba arXiv: https://arxiv.org/abs/2312.00752

**Core idea:** These works explore non-standard or attention-free long-sequence architectures:
structured state spaces, long convolutions with gating, and selective state-space models.

**Why it matters to us:** These are roadmap knowledge, not MVP build instructions. They are relevant
because AMD ACT II has long event streams and time-series-ish operational history. In the future,
specialized sequence models could help with forecasting, anomaly detection, or compressed event
memory. Today, the LLM ecosystem, vLLM serving path, and hackathon constraints make Transformer LLMs
the practical choice.

**Project takeaway:**
- Keep the architecture model-agnostic so future sequence models can be evaluated later.
- Do not bind business logic to one model family.

**MVP action:**
- No custom SSM/Mamba/Hyena model.
- Keep inference behind one provider-neutral client.

### 2.14 vLLM And PagedAttention - Kwon et al. (2023)

**Primary and official sources:**
- arXiv: https://arxiv.org/abs/2309.06180
- vLLM project blog: https://vllm.ai/blog/2023-06-20-vllm
- Current vLLM GPU installation docs: https://docs.vllm.ai/en/latest/getting_started/installation/gpu/
- AMD ROCm vLLM inference docs: https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference/benchmark-docker/vllm.html

**Core idea:** PagedAttention manages attention key/value cache memory using paging-inspired block
management. vLLM builds an LLM serving engine around that idea.

**Why it matters to us:** This is the most directly actionable item in category 2. AMD ACT II already
locks in one OpenAI-compatible inference client with Fireworks fallback and vLLM-on-MI300X proof path.
PagedAttention explains why vLLM is a sensible serving choice: LLM serving is heavily shaped by KV
cache memory, batching, scheduling, and throughput.

The current official docs also matter: vLLM documents AMD ROCm GPU support, and AMD documents a
ROCm-enabled vLLM Docker path for AMD Instinct GPUs including MI300X-class hardware.

**Project takeaway:**
- The inference gateway is a real architecture boundary, not plumbing.
- The demo should show the vLLM endpoint, model, latency, token count, and provider switch.
- Fireworks and vLLM should share the same OpenAI-compatible client interface.

**MVP action:**
- Keep `INFERENCE_PROVIDER=fireworks|vllm` style switching.
- Capture a trace showing which provider served each call.
- Log prompt tokens, completion tokens, latency, and approximate cost/throughput.
- Keep the MI300X proof measurable even if the public demo uses Fireworks fallback.

## Project Takeaways From Category 2

### A. Attention Is Context Economics

Every token competes for compute, memory, and model focus. AMD ACT II should treat context as a scarce
resource. The best prompt is not the longest prompt; it is the prompt with the right facts in the
right order.

### B. The Context Builder Is Product Logic

The context builder decides what each agent can know. It should be deterministic, testable, and
auditable. It should include global policy anchors, current event facts, compact retrieved memory,
and exact source refs.

### C. KV Cache Is An Operational Resource

MQA, GQA, PagedAttention, and vLLM all point to the same fact: decoding cost is deeply tied to KV
cache memory. Multi-agent fan-out has real serving cost. Selective firing is not only simpler; it is
more scalable.

### D. Long Context Does Not Replace RAG Or Contracts

RoPE, ALiBi, Transformer-XL, Longformer, and BigBird all improve long-sequence handling in different
ways. None of them mean we should dump all data into the model. RAG, summaries, contracts, and
decision memory remain the correct product pattern.

### E. Model Choice Must Include Serving Architecture

For the selected model, track:

- context window.
- GQA/MQA or attention architecture.
- vLLM support.
- ROCm/MI300X support.
- quantization support.
- structured JSON reliability.
- measured latency and throughput.

### F. Use Existing Runtime Optimizations

FlashAttention and vLLM are evidence that optimized runtimes matter. The MVP should use supported
serving paths rather than custom kernels or custom model internals.

### G. Alternative Sequence Models Are Roadmap, Not MVP

S4, Hyena, and Mamba are worth knowing, especially for long event streams and future forecasting, but
they should not distract from the current architecture: Transformer LLMs behind one inference client.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep one OpenAI-compatible inference client | Transformer, vLLM/PagedAttention | Allows Fireworks fallback and vLLM/MI300X proof without app rewrites |
| Keep reliable context target around 16K-24K | RoPE, ALiBi, long-context papers | Long context is not automatically reliable context |
| Use compact evidence contracts | Attention, Longformer, BigBird | Attention should spend budget on grounded facts and policy anchors |
| Keep selective 5-agent spine | MQA, GQA, PagedAttention | Each agent call creates decode and KV-cache cost |
| Use RAG/memory summaries, not raw logs | Transformer-XL, Longformer | Temporal history must be compact and coherent |
| Show MI300X/vLLM metrics | FlashAttention, FlashAttention-2, vLLM | Runtime and memory behavior are part of the technology story |
| Avoid custom attention/model internals | Reformer, Linformer, Performer | Efficient attention research is valuable, but MVP reliability comes from proven runtimes |
| Keep model-agnostic business logic | S4, Hyena, Mamba | Future sequence models should be replaceable behind the inference boundary |

## What We Are Not Using Yet

- No custom Transformer training.
- No custom attention kernels.
- No custom long-context model.
- No SSM/Mamba/Hyena implementation.
- No raw transcript stuffing.
- No "all agents always run" architecture.
- No claiming MI300X performance without an actual measured trace.

These papers guide the architecture, but the MVP remains a practical product system: contract-first
agents, deterministic orchestration, RAG/memory, critic review, HITL, and measurable vLLM/MI300X
inference.

## Category 2 Source List

- Vaswani et al., "Attention Is All You Need" (2017): https://arxiv.org/abs/1706.03762
- Dai et al., "Transformer-XL: Attentive Language Models Beyond a Fixed-Length Context" (2019):
  https://arxiv.org/abs/1901.02860
- Kitaev, Kaiser, Levskaya, "Reformer: The Efficient Transformer" (2020):
  https://arxiv.org/abs/2001.04451
- Beltagy, Peters, Cohan, "Longformer: The Long-Document Transformer" (2020):
  https://arxiv.org/abs/2004.05150
- Zaheer et al., "Big Bird: Transformers for Longer Sequences" (2020):
  https://arxiv.org/abs/2007.14062
- Wang et al., "Linformer: Self-Attention with Linear Complexity" (2020):
  https://arxiv.org/abs/2006.04768
- Choromanski et al., "Rethinking Attention with Performers" (2020):
  https://arxiv.org/abs/2009.14794
- Dao et al., "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness" (2022):
  https://arxiv.org/abs/2205.14135
- Dao, "FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning" (2023):
  https://arxiv.org/abs/2307.08691
- Shazeer, "Fast Transformer Decoding: One Write-Head is All You Need" (2019):
  https://arxiv.org/abs/1911.02150
- Ainslie et al., "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head
  Checkpoints" (2023): https://arxiv.org/abs/2305.13245
- Su et al., "RoFormer: Enhanced Transformer with Rotary Position Embedding" (2021):
  https://arxiv.org/abs/2104.09864
- Press, Smith, Lewis, "Train Short, Test Long: Attention with Linear Biases Enables Input Length
  Extrapolation" (2021): https://arxiv.org/abs/2108.12409
- Gu, Goel, Re, "Efficiently Modeling Long Sequences with Structured State Spaces" (2021):
  https://arxiv.org/abs/2111.00396
- Poli et al., "Hyena Hierarchy: Towards Larger Convolutional Language Models" (2023):
  https://arxiv.org/abs/2302.10866
- Gu, Dao, "Mamba: Linear-Time Sequence Modeling with Selective State Spaces" (2023):
  https://arxiv.org/abs/2312.00752
- Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention"
  (2023): https://arxiv.org/abs/2309.06180
- vLLM official GPU installation docs: https://docs.vllm.ai/en/latest/getting_started/installation/gpu/
- AMD ROCm vLLM inference docs:
  https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference/benchmark-docker/vllm.html

---

# 3. Language Models

## Why This Category Matters

Language models are the engine behind the AMD ACT II agents. This category decides how we think about
model families, not just famous papers. The project does not need the biggest model everywhere. It
needs the right model per job: reliable structured JSON, grounded reasoning over operational evidence,
tool-use friendliness, low enough latency for a live cascade, and compatibility with Fireworks plus
vLLM-on-ROCm/MI300X.

The key product question is not "what is the smartest model in the world?" It is:

**What model policy gives the demo reliable decisions, auditable traces, acceptable latency, and a
credible AMD open-inference story?**

This section focuses on papers and model families that influence that policy.

## Selected Papers And Model Families

### 3.1 Word2Vec And GloVe - Mikolov et al. (2013), Pennington et al. (2014)

**Primary sources:**
- Word2Vec arXiv: https://arxiv.org/abs/1301.3781
- GloVe ACL Anthology: https://aclanthology.org/D14-1162/
- GloVe Stanford project page: https://nlp.stanford.edu/projects/glove/

**Core idea:** Distributional embeddings turn words into vectors based on usage patterns. Word2Vec
learns predictive word representations; GloVe uses global word co-occurrence statistics.

**Why it matters to us:** These are not model candidates for the MVP, but they are the root of vector
retrieval thinking. AMD ACT II's memory/RAG layer depends on the same principle: semantically similar
items should be close enough to retrieve.

**Project takeaway:**
- Vector search is useful, but raw similarity is not proof. Retrieval must return source refs,
  timestamps, SKU/store scope, and enough metadata for the Critic to verify claims.

**MVP action:**
- Do not use Word2Vec/GloVe as production embeddings.
- Keep this as background for why pgvector and retrieval scoring matter.

### 3.2 ELMo, BERT, And RoBERTa - Peters et al. (2018), Devlin et al. (2018), Liu et al. (2019)

**Primary sources:**
- ELMo arXiv: https://arxiv.org/abs/1802.05365
- ELMo ACL Anthology: https://aclanthology.org/N18-1202/
- BERT arXiv: https://arxiv.org/abs/1810.04805
- BERT ACL Anthology: https://aclanthology.org/N19-1423/
- RoBERTa arXiv: https://arxiv.org/abs/1907.11692

**Core idea:** Contextual representations replaced static word vectors. BERT-style encoders are strong
for understanding, classification, reranking, extraction, and question answering. RoBERTa showed that
training recipe and data scale can matter as much as architectural novelty.

**Why it matters to us:** AMD ACT II needs generation for agents, so BERT-style encoders are not the
main agent model. But encoders remain useful for:

- Embeddings and reranking.
- Matching events to product records.
- Classifying noisy inbound text.
- Extracting structured facts from CSV notes or free text.

RoBERTa also gives an engineering lesson: do not over-credit a model architecture until the training,
data, and evaluation setup are controlled.

**Project takeaway:**
- Use decoder/instruction models for agent decisions.
- Use encoder/reranker models where retrieval quality matters.
- Treat benchmark claims carefully; evaluate on the golden scenario.

**MVP action:**
- Keep retrieval/reranking as a separable component.
- Do not ask a generator to solve every matching/ranking problem when a small encoder can do it
  cheaper and more predictably.

### 3.3 ALBERT And DistilBERT - Lan et al. (2019), Sanh et al. (2019)

**Primary sources:**
- ALBERT arXiv: https://arxiv.org/abs/1909.11942
- DistilBERT arXiv: https://arxiv.org/abs/1910.01108

**Core idea:** Smaller models can retain much of a larger model's utility through parameter sharing,
factorization, or distillation.

**Why it matters to us:** The details of ALBERT/DistilBERT are not central to the MVP, but the
principle is central: a smaller model that is good enough and fast enough can be better product
engineering than a larger model that slows the cascade.

**Project takeaway:**
- Optimize for the whole cascade, not a single-model benchmark.
- Consider distilled or smaller models for routine agents, guards, extraction, and classification.

**MVP action:**
- Define a model-routing policy: routine agents on smaller models; Executive/Critic on a stronger
  model only if evals justify the cost.

### 3.4 GPT, GPT-2, GPT-3, And GPT-4 - OpenAI (2018-2023)

**Primary sources:**
- GPT paper PDF: https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf
- GPT-2 paper PDF: https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf
- GPT-3 arXiv: https://arxiv.org/abs/2005.14165
- GPT-4 Technical Report arXiv: https://arxiv.org/abs/2303.08774

**Core idea:** Decoder-only generative pretraining scaled into few-shot, instruction-following, and
general assistant behavior. GPT-3 made in-context learning central. GPT-4 showed a high-capability
closed frontier model with broad benchmark strength and safety/evaluation reporting.

**Why it matters to us:** The AMD ACT II agent pattern is GPT-style: give instructions, facts, schema,
and examples; receive a structured answer. But the project should not depend on closed GPT models.
They are useful as a design reference and, if needed, an external quality baseline, not the core
hackathon story.

**Project takeaway:**
- Few-shot prompting works, but examples consume context.
- Structured output must be validated; do not trust a fluent answer because it sounds confident.
- Closed frontier models can be used as reference points, but the product thesis is open-model
  inference with an AMD proof path.

**MVP action:**
- Keep one OpenAI-compatible client, but do not hardcode OpenAI-specific behavior.
- Use schema validation, retry once, critic review, and safe defaults for every model.
- If a closed model is ever used as an evaluator, label it as evaluator/fallback, not the core engine.

### 3.5 T5 And FLAN-T5 - Raffel et al. (2020), Chung et al. (2022)

**Primary sources:**
- T5 JMLR: https://jmlr.org/papers/v21/20-074.html
- T5 arXiv: https://arxiv.org/abs/1910.10683
- FLAN instruction tuning arXiv: https://arxiv.org/abs/2210.11416

**Core idea:** T5 frames language tasks as text-to-text transfer. FLAN-style instruction tuning shows
that training on many instruction-formatted tasks improves zero-shot/few-shot usability.

**Why it matters to us:** AMD ACT II agents are instruction-driven. The relevant lesson is that
instruction tuning and task formatting matter. A base model is not enough; use an instruction-tuned
model for agent outputs.

**Project takeaway:**
- Model choice should prefer instruction-tuned/chat variants for agents.
- Prompt format should be stable and task-like: objective, facts, constraints, output schema.

**MVP action:**
- Do not use base pretrained checkpoints for production agent calls.
- Version prompt templates and model ids together.

### 3.6 PaLM, PaLM 2, And Chinchilla - Google/DeepMind (2022-2023)

**Primary sources:**
- PaLM arXiv: https://arxiv.org/abs/2204.02311
- PaLM 2 arXiv: https://arxiv.org/abs/2305.10403
- Chinchilla arXiv: https://arxiv.org/abs/2203.15556

**Core idea:** PaLM showed continued benefits from large-scale language-model training and distributed
systems. PaLM 2 emphasized multilingual/reasoning efficiency. Chinchilla showed that many very large
models were undertrained relative to available compute and that smaller models trained on more data
can outperform larger undertrained models.

**Why it matters to us:** Chinchilla is the most useful paper here for product engineering. It argues
against "bigger by default." For a live operations OS, a well-trained 7B-32B model may beat a larger
model on latency/cost/reliability if the task and context are controlled.

**Project takeaway:**
- Choose models by measured task performance per rand/second, not parameter count.
- Smaller well-trained open models are often the practical default.
- The model-routing policy should be empirical.

**MVP action:**
- Benchmark at least one small/mid open model and one stronger model on the golden scenario.
- Track JSON validity, critic agreement, latency, and token cost, not just subjective answer quality.

### 3.7 Llama 2, Llama 3, And Llama 4 - Meta (2023-2025)

**Primary and official sources:**
- Llama 2 arXiv: https://arxiv.org/abs/2307.09288
- Llama 2 Meta research page: https://ai.meta.com/research/publications/llama-2-open-foundation-and-fine-tuned-chat-models/
- Llama 3 arXiv: https://arxiv.org/abs/2407.21783
- Llama 3 Meta research page: https://ai.meta.com/research/publications/the-llama-3-herd-of-models/
- Llama 3.1 Meta announcement: https://ai.meta.com/blog/meta-llama-3-1/
- Llama 4 Meta announcement: https://ai.meta.com/blog/llama-4-multimodal-intelligence/

**Core idea:** Llama made strong open-weight foundation models a serious production option. Llama 2
released 7B-70B pretrained/chat models. Llama 3 expanded capability, context, multilinguality,
coding, reasoning, and tool use, including a 405B model. Meta's 2025 Llama 4 announcement moved the
family toward natively multimodal, mixture-of-experts models.

**Why it matters to us:** Llama is a natural baseline family for AMD ACT II because it is widely
served, widely benchmarked, and commonly supported by inference runtimes. Llama 3/3.1-style models
are especially relevant for tool-use and agent tasks. Llama 4 may be relevant to roadmap scanner and
multimodal flows, but it must be checked against vLLM/ROCm support, license terms, and actual
structured-output behavior before selection.

**Project takeaway:**
- Llama-family models should be part of the candidate set for Fireworks/vLLM.
- Do not say "open source" loosely. Track actual license and usage constraints.
- Multimodal Llama 4 belongs to roadmap evaluation, not automatic MVP adoption.

**MVP action:**
- Candidate routine model: Llama 3.x 8B-class or similar if it passes JSON/evidence tests.
- Candidate stronger model: Llama 3.x 70B-class if latency and provider support are acceptable.
- Record the exact model id and license in a model card.

### 3.8 Mistral 7B And Mixtral - Mistral AI (2023-2024)

**Primary sources:**
- Mistral 7B arXiv: https://arxiv.org/abs/2310.06825
- Mixtral arXiv: https://arxiv.org/abs/2401.04088

**Core idea:** Mistral 7B showed strong small-model performance with grouped-query attention and
sliding-window attention. Mixtral 8x7B used sparse mixture-of-experts to activate only part of the
model per token while providing stronger capability.

**Why it matters to us:** These are directly relevant to AMD ACT II because they connect model quality
to serving efficiency. A strong 7B or sparse MoE model can be a better demo choice than a large dense
model if it gives fast, stable, schema-valid answers.

**Project takeaway:**
- Small efficient models can power routine agents.
- MoE models can provide stronger capability, but routing/serving support must be tested.

**MVP action:**
- Include at least one Mistral-family or Mixtral-family candidate in model evaluation if available on
  the selected provider/runtime.
- Measure JSON validity and latency, not just benchmark reputation.

### 3.9 DeepSeek-V3 And DeepSeek-R1 - DeepSeek AI (2024-2025)

**Primary sources:**
- DeepSeek-V3 arXiv: https://arxiv.org/abs/2412.19437
- DeepSeek-R1 arXiv: https://arxiv.org/abs/2501.12948
- DeepSeek-R1 GitHub: https://github.com/deepseek-ai/deepseek-r1

**Core idea:** DeepSeek-V3 is a large MoE language model designed for efficient training and inference.
DeepSeek-R1 focuses on reasoning capability via reinforcement learning and released distilled dense
models based on Qwen and Llama families.

**Why it matters to us:** DeepSeek is relevant in two different ways:

- V3-style models are general assistants with strong cost/performance engineering.
- R1-style models are useful for reasoning-heavy critique, simulation review, or executive analysis,
  but may be slower or more verbose than needed for routine agents.

**Project takeaway:**
- Reasoning models are not automatically the best default. Use them for Critic/Executive only when
  evals show better decisions.
- Distilled reasoning models may be practical candidates for the Critic if they keep output
  structured and concise.

**MVP action:**
- Consider DeepSeek-R1 distill candidates for Critic/Executive evals.
- Do not use long hidden reasoning as the UI trace. The UI trace should show evidence, verdict,
  decision, and source refs.

### 3.10 Gemma, Gemma 2, And Gemma 3 - Google DeepMind (2024-2025)

**Primary sources:**
- Gemma arXiv: https://arxiv.org/abs/2403.08295
- Gemma 2 arXiv: https://arxiv.org/abs/2408.00118
- Gemma 3 arXiv: https://arxiv.org/abs/2503.19786

**Core idea:** Gemma is a family of lightweight open models based on Gemini research. Gemma 2 improved
practical-size open models with changes such as local/global attention and GQA. Gemma 3 added
multimodal capability, broader languages, longer context, and KV-cache-conscious design.

**Why it matters to us:** Gemma is relevant because it targets practical deployment sizes. For AMD
ACT II, Gemma-family models could serve as lightweight candidates for routine agents or future
multimodal scanner flows.

**Project takeaway:**
- Practical-size models deserve evaluation before defaulting to larger models.
- Multimodal capability is roadmap-relevant, but scanner reliability can remain deterministic for
  the MVP.

**MVP action:**
- Consider Gemma 2/3-size candidates only if provider/runtime support and license fit the project.
- Keep scanner simulation fallback regardless of multimodal model availability.

### 3.11 Qwen2.5 And Qwen3 - Qwen Team (2024-2025)

**Primary sources:**
- Qwen2.5 arXiv: https://arxiv.org/abs/2412.15115
- Qwen3 arXiv: https://arxiv.org/abs/2505.09388

**Core idea:** Qwen2.5 and Qwen3 provide broad open-weight model families with strong multilingual,
coding, reasoning, structured-data, and MoE/dense variants across many sizes.

**Why it matters to us:** Qwen was not in the user's original list, but it is highly relevant to AMD
ACT II because the project needs structured data analysis, multilingual robustness, coding/tool
behavior, and model sizes that can fit different serving budgets. DeepSeek-R1 distills also use Qwen
bases, making the family part of the current open-model ecosystem.

**Project takeaway:**
- Qwen-family models should be in the candidate set for structured-output and operations-analysis
  evaluation.
- Multilingual capability may matter in South African contexts even if the MVP data is mostly English.

**MVP action:**
- Evaluate a Qwen instruct model for JSON reliability, SKU/store reasoning, and short action
  recommendations.
- Keep model choice behind config so Qwen/Llama/Mistral/Gemma/DeepSeek candidates can be swapped.

### 3.12 Fireworks Model Availability And Provider Reality

**Official source:** Fireworks changelog: https://docs.fireworks.ai/updates/changelog

**Core idea:** Hosted provider catalogs change. Fireworks documents support for model families such
as Qwen, Phi, Gemma, Llama, DeepSeek, and related fine-tuning/serverless updates.

**Why it matters to us:** AMD ACT II already plans Fireworks as the reliable development/public-demo
fallback. The fallback model cannot be chosen from memory; it must be checked against the current
provider catalog and pricing close to demo time.

**Project takeaway:**
- Model availability is operational state, not static architecture.
- Provider choice belongs in config and docs, not hardcoded in business logic.

**MVP action:**
- Before implementation/demo, pick exact provider model ids from current Fireworks and vLLM support.
- Add a model card with date checked, provider, model id, context, license, latency, JSON pass rate,
  and fallback model.

## Project Takeaways From Category 3

### A. Use The Smallest Model That Passes The Product Eval

Chinchilla, DistilBERT, ALBERT, Mistral, Gemma, and Qwen all push the same product rule: do not pay
for size unless it improves the measured cascade.

### B. Agent Models Should Be Instruction-Tuned

T5/FLAN and the modern chat/instruct model families show that format and instruction tuning matter.
AMD ACT II agents should use instruction-tuned models, not base checkpoints.

### C. Open-Weight Model Choice Is A Runtime Decision

Llama, Mistral, Mixtral, Gemma, Qwen, and DeepSeek are all plausible candidates. The project should
not bind the domain logic to one family. The inference gateway should isolate model/provider choice.

### D. JSON Reliability Is A First-Class Metric

The best benchmark model may still be the wrong product model if it fails schemas. AMD ACT II should
measure:

- valid JSON rate.
- valid `EvidenceObject` rate.
- hallucinated source rate.
- critic agreement.
- latency per agent.
- total cascade latency.
- cost/tokens.

### E. Use Bigger Or Reasoning Models Sparingly

DeepSeek-R1 and GPT-4-style reasoning strength is useful, but not every agent needs maximum reasoning.
Routine inventory/expiry/demand passes can use smaller models if the context and schema are strong.
Executive and Critic can route to a stronger model only when risk or evals justify it.

### F. Encoders Still Matter

BERT/RoBERTa-style models are not the main generative agent engine, but they remain relevant for
retrieval, reranking, classification, entity matching, and extraction.

### G. License And Provider Terms Are Part Of Engineering

"Open" is not one thing. Track license, commercial restrictions, acceptable use terms, provider
availability, and whether the model can be served on MI300X/vLLM.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep one provider-neutral inference client | GPT lineage, Llama, Mistral, Gemma, Qwen, DeepSeek | Model families change; business logic should not |
| Use instruction-tuned models for agents | FLAN-T5, GPT-3, Llama chat/instruct, Qwen instruct | Agents need task-following and schema obedience |
| Evaluate model candidates on golden scenario | RoBERTa, Chinchilla, GPT-4 report | Benchmarks and scale claims are not enough |
| Use smaller routine models when they pass | DistilBERT, Chinchilla, Mistral, Gemma | Lower latency/cost improves the live cascade |
| Route stronger models to Executive/Critic only when justified | GPT-4, DeepSeek-R1, PaLM | Reasoning is valuable but expensive and sometimes verbose |
| Keep retrieval/reranking separate from generation | Word2Vec, GloVe, BERT, RoBERTa | Semantic matching is not the same job as action recommendation |
| Version model ids, prompts, and eval results | FLAN, Llama, Qwen, Fireworks docs | Reproducibility requires exact model/config records |
| Avoid closed-model dependency in the core story | Llama, Mistral, Gemma, Qwen, DeepSeek | Hackathon thesis is open-model inference with AMD proof |

## Model Evaluation Matrix For AMD ACT II

When implementation begins, evaluate candidates with this checklist:

| Dimension | Must Capture |
|---|---|
| Identity | provider, exact model id, version/date checked |
| License | license name, commercial restrictions, acceptable use notes |
| Runtime | Fireworks support, vLLM support, ROCm/MI300X status |
| Context | max context, reliable tested context, prompt/completion token limits |
| Architecture | dense/MoE, GQA/MQA/MLA if known, quantization support |
| Quality | golden scenario pass, per-agent pass, critic rejection behavior |
| Structure | JSON validity, schema validity, source-ref honesty |
| Cost | prompt tokens, completion tokens, latency, throughput, provider price if hosted |
| Safety | refusal behavior, hallucinated actions, high-risk escalation, HITL compatibility |

## Candidate Policy For The MVP

Start with a model policy, not a single favorite model:

- **Routine agents:** small/mid instruct model, likely 7B-32B class, chosen by JSON validity and
  latency.
- **Executive:** stronger instruct model only if it improves action quality.
- **Critic:** strongest cost-acceptable model for evidence checking, possibly a reasoning-distilled
  model if it stays concise and schema-valid.
- **Embeddings/reranking:** separate encoder/embedding model, not the agent generator.
- **Fallback:** Fireworks-hosted model with same OpenAI-compatible client contract.
- **AMD proof:** vLLM-served open model on ROCm/MI300X with measured trace.

## What We Are Not Using Yet

- No closed-model dependency as the main product engine.
- No base pretrained checkpoints for agent decisions.
- No parameter-count-based model choice.
- No hardcoded provider/model ids inside business logic.
- No using GPT-4 as the hackathon proof path.
- No assuming "open source" without checking license.
- No reasoning-model UI traces that expose private chain-of-thought-like content.

## Category 3 Source List

- Mikolov et al., "Efficient Estimation of Word Representations in Vector Space" (2013):
  https://arxiv.org/abs/1301.3781
- Pennington, Socher, Manning, "GloVe: Global Vectors for Word Representation" (2014):
  https://aclanthology.org/D14-1162/
- Peters et al., "Deep contextualized word representations" (2018):
  https://arxiv.org/abs/1802.05365
- Devlin et al., "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
  (2018/2019): https://arxiv.org/abs/1810.04805
- Liu et al., "RoBERTa: A Robustly Optimized BERT Pretraining Approach" (2019):
  https://arxiv.org/abs/1907.11692
- Lan et al., "ALBERT: A Lite BERT for Self-supervised Learning of Language Representations" (2019):
  https://arxiv.org/abs/1909.11942
- Sanh et al., "DistilBERT, a distilled version of BERT" (2019):
  https://arxiv.org/abs/1910.01108
- Radford et al., "Improving Language Understanding by Generative Pre-Training" (2018):
  https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf
- Radford et al., "Language Models are Unsupervised Multitask Learners" (2019):
  https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf
- Brown et al., "Language Models are Few-Shot Learners" (2020):
  https://arxiv.org/abs/2005.14165
- OpenAI, "GPT-4 Technical Report" (2023):
  https://arxiv.org/abs/2303.08774
- Raffel et al., "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer"
  (2020): https://jmlr.org/papers/v21/20-074.html
- Chung et al., "Scaling Instruction-Finetuned Language Models" (2022):
  https://arxiv.org/abs/2210.11416
- Chowdhery et al., "PaLM: Scaling Language Modeling with Pathways" (2022):
  https://arxiv.org/abs/2204.02311
- Anil et al., "PaLM 2 Technical Report" (2023):
  https://arxiv.org/abs/2305.10403
- Hoffmann et al., "Training Compute-Optimal Large Language Models" (2022):
  https://arxiv.org/abs/2203.15556
- Touvron et al., "Llama 2: Open Foundation and Fine-Tuned Chat Models" (2023):
  https://arxiv.org/abs/2307.09288
- Meta, "The Llama 3 Herd of Models" (2024):
  https://arxiv.org/abs/2407.21783
- Meta, "Introducing Llama 3.1" (2024):
  https://ai.meta.com/blog/meta-llama-3-1/
- Meta, "The Llama 4 herd" (2025):
  https://ai.meta.com/blog/llama-4-multimodal-intelligence/
- Jiang et al., "Mistral 7B" (2023):
  https://arxiv.org/abs/2310.06825
- Jiang et al., "Mixtral of Experts" (2024):
  https://arxiv.org/abs/2401.04088
- DeepSeek-AI, "DeepSeek-V3 Technical Report" (2024):
  https://arxiv.org/abs/2412.19437
- DeepSeek-AI, "DeepSeek-R1" (2025):
  https://arxiv.org/abs/2501.12948
- Gemma Team, "Gemma: Open Models Based on Gemini Research and Technology" (2024):
  https://arxiv.org/abs/2403.08295
- Gemma Team, "Gemma 2: Improving Open Language Models at a Practical Size" (2024):
  https://arxiv.org/abs/2408.00118
- Gemma Team, "Gemma 3 Technical Report" (2025):
  https://arxiv.org/abs/2503.19786
- Qwen Team, "Qwen2.5 Technical Report" (2024):
  https://arxiv.org/abs/2412.15115
- Qwen Team, "Qwen3 Technical Report" (2025):
  https://arxiv.org/abs/2505.09388
- Fireworks AI changelog/model support notes:
  https://docs.fireworks.ai/updates/changelog

---

# 4. Fine-Tuning And Adaptation

## Why This Category Matters

Fine-tuning is not an MVP requirement for AMD ACT II, but it is a serious roadmap lever. The MVP
should first prove that prompting, RAG, tools, schemas, deterministic simulation, and critic review
can produce reliable decisions. Fine-tuning becomes useful only after we have data: golden scenarios,
approved/rejected decisions, source-linked examples, critic verdicts, and real user corrections.

This category answers one question:

**When AMD ACT II has enough domain data, how can we adapt open models without retraining everything
or breaking the serving story?**

## Selected Papers And Methods

### 4.1 Adapters - Houlsby et al. (2019)

**Primary source:** https://arxiv.org/abs/1902.00751

Adapters insert small trainable modules into a frozen pretrained model. They were designed for
parameter-efficient transfer across many downstream tasks.

**Project takeaway:** If AMD ACT II eventually needs tenant-specific or domain-specific adaptation,
adapter-style methods support the idea of keeping one shared base model while storing small
task/tenant adapters.

**MVP action:** No training. Keep model/prompt/eval records so future adaptation examples are clean.

### 4.2 Prefix Tuning And Prompt Tuning - Li & Liang (2021), Lester et al. (2021)

**Primary sources:**
- Prefix tuning: https://arxiv.org/abs/2101.00190
- Prompt tuning: https://arxiv.org/abs/2104.08691

These methods keep the model frozen and learn continuous prompt-like vectors. They are useful
historically because they separate task adaptation from full weight updates.

**Project takeaway:** A stable base model can be specialized by small learned artifacts. For AMD ACT
II, the non-training equivalent is versioned prompt templates and system instructions.

**MVP action:** Treat prompt templates as versioned assets with eval results, not throwaway strings.

### 4.3 LoRA - Hu et al. (2021)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2106.09685
- OpenReview: https://openreview.net/forum?id=nZeVKeeFYf9

LoRA freezes pretrained weights and injects trainable low-rank matrices into Transformer layers,
dramatically reducing trainable parameters and GPU memory.

**Project takeaway:** LoRA is the most practical future fine-tuning path for domain-specific AMD ACT
II agents. It is especially relevant if we collect enough approved decision examples and want a model
that follows our evidence contract with less prompt overhead.

**MVP action:** Store future fine-tuning candidates now: input context, expected `EvidenceObject`,
critic result, human approval result, and final action.

### 4.4 BitFit - Ben Zaken, Ravfogel, Goldberg (2021)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2106.10199
- ACL Anthology: https://aclanthology.org/2022.acl-short.1/

BitFit tunes only bias terms. It is less central for modern LLM adaptation than LoRA, but it is a
useful reminder that tiny updates can matter.

**Project takeaway:** Do not assume adaptation requires massive infrastructure. The first useful
domain improvement may come from small, controlled changes.

**MVP action:** Keep adaptation as a roadmap slide, not an MVP dependency.

### 4.5 IA3 / T-Few - Liu et al. (2022)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2205.05638
- OpenReview: https://openreview.net/forum?id=rBCvMG-JsPd

IA3 scales internal activations with learned vectors. The T-Few work compares parameter-efficient
fine-tuning with in-context learning and shows that PEFT can be better and cheaper for some tasks.

**Project takeaway:** If AMD ACT II repeatedly performs the same structured tasks, PEFT can reduce
inference-time prompt bloat. But first we need reliable labeled examples.

**MVP action:** Do not overuse few-shot examples in every prompt. Keep prompts compact and rely on
contracts/evals.

### 4.6 QLoRA - Dettmers et al. (2023)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2305.14314
- official code: https://github.com/artidoro/qlora

QLoRA backpropagates through a frozen 4-bit quantized model into LoRA adapters, making fine-tuning
large models dramatically cheaper.

**Project takeaway:** QLoRA is the strongest roadmap method if we want to fine-tune a larger open
model on AMD ACT II data without full training cost. It also reinforces the model-card requirement:
quantization, runtime, memory, and adapter compatibility must be tracked.

**MVP action:** Design decision logs so they can become SFT/QLoRA data later.

### 4.7 AdaLoRA - Zhang et al. (2023)

**Primary source:** https://arxiv.org/abs/2303.10512

AdaLoRA adaptively allocates LoRA rank/budget across weights based on importance.

**Project takeaway:** When adaptation becomes real, budget allocation matters. For now, this means
fine-tuning experiments need evals, not vibes.

**MVP action:** Future fine-tuning experiments should report schema pass rate, hallucinated-source
rate, latency, and golden scenario score before being kept.

## Project Takeaways From Category 4

### A. Fine-Tuning Comes After Data

The MVP should not fine-tune because we do not yet have real, trusted examples. The right order is:
ship deterministic demo -> log decisions -> collect feedback -> curate training data -> adapt.

### B. The Decision Log Is Future Training Data

Every decision should store the triggering event, context, evidence, recommendation, critic verdict,
human decision, and outcome. That is the raw material for SFT, DPO, LoRA, or QLoRA later.

### C. PEFT Beats Full Fine-Tuning For Our Roadmap

Adapters, LoRA, QLoRA, IA3, and prompt tuning all support a lightweight adaptation strategy. AMD ACT
II should avoid full fine-tuning unless there is a clear future reason.

### D. Prompt Versioning Is The MVP Equivalent Of Adaptation

Before training adapters, version prompts, model ids, schemas, and eval results. Prompt drift without
versioning is just untracked fine-tuning by hand.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Do not fine-tune in MVP | LoRA, QLoRA, IA3 | Adaptation needs clean data first |
| Store complete decision traces | LoRA, DPO, QLoRA | Future training needs high-quality examples |
| Version prompts/model ids | Prompt tuning, FLAN, PEFT | Reproducibility requires exact config |
| Use open models with adapter support | LoRA, QLoRA | Roadmap adaptation should not require vendor lock-in |
| Evaluate adaptation by product metrics | AdaLoRA, QLoRA | Parameter efficiency is not enough; schema/evidence quality matters |

## What We Are Not Using Yet

- No fine-tuning before the MVP.
- No tenant-specific adapters before real tenant data.
- No synthetic fine-tuning data that is not validated by evals.
- No full-model training.
- No adapter work that breaks vLLM/Fireworks compatibility.

## Category 4 Source List

- Houlsby et al., "Parameter-Efficient Transfer Learning for NLP" (2019):
  https://arxiv.org/abs/1902.00751
- Li and Liang, "Prefix-Tuning: Optimizing Continuous Prompts for Generation" (2021):
  https://arxiv.org/abs/2101.00190
- Lester, Al-Rfou, Constant, "The Power of Scale for Parameter-Efficient Prompt Tuning" (2021):
  https://arxiv.org/abs/2104.08691
- Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models" (2021):
  https://arxiv.org/abs/2106.09685
- Ben Zaken, Ravfogel, Goldberg, "BitFit" (2021):
  https://arxiv.org/abs/2106.10199
- Liu et al., "Few-Shot Parameter-Efficient Fine-Tuning is Better and Cheaper than In-Context
  Learning" (2022): https://arxiv.org/abs/2205.05638
- Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs" (2023):
  https://arxiv.org/abs/2305.14314
- Zhang et al., "AdaLoRA: Adaptive Budget Allocation for Parameter-Efficient Fine-Tuning" (2023):
  https://arxiv.org/abs/2303.10512

---

# 5. Reinforcement Learning And Preference Optimization

## Why This Category Matters

Classic reinforcement learning is not a direct MVP dependency. AMD ACT II is not training a physical
control policy. But preference optimization is highly relevant because the system recommends actions
that humans approve, reject, or revise. That means the product can eventually learn what "good" means
from outcomes and human decisions.

The MVP version is not RL training. It is **preference-data capture**.

## Selected Papers And Methods

### 5.1 DQN - Mnih et al. (2015)

**Primary source:** Nature: https://www.nature.com/articles/nature14236

DQN showed that a neural agent can learn policies from high-dimensional observations through
interaction and reward.

**Project takeaway:** Agents improve when feedback is explicit. In AMD ACT II, reward signals are not
game scores; they are approval decisions, recovered rand, waste reduction, stockout avoidance, and
critic verdicts.

**MVP action:** Log action outcomes and human decisions, even if no RL is trained yet.

### 5.2 TRPO, PPO, And SAC - Schulman et al. (2015/2017), Haarnoja et al. (2018)

**Primary sources:**
- TRPO: https://arxiv.org/abs/1502.05477
- PPO: https://arxiv.org/abs/1707.06347
- SAC: https://arxiv.org/abs/1801.01290

TRPO and PPO focus on stable policy optimization. SAC emphasizes maximum-entropy exploration and
more stable off-policy learning.

**Project takeaway:** The practical lesson is not to implement these algorithms now. The lesson is
that action policies need guardrails, stability, and feedback loops. Business operations cannot
tolerate unconstrained exploration.

**MVP action:** Recommend-only, HITL-gated actions are correct. No autonomous write-back.

### 5.3 RLHF / InstructGPT - Ouyang et al. (2022)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2203.02155
- NeurIPS PDF: https://proceedings.neurips.cc/paper_files/paper/2022/file/b1efde53be364a73914f58805a001731-Paper-Conference.pdf

InstructGPT showed that human feedback and rankings can make smaller models more aligned with user
intent than a much larger base model.

**Project takeaway:** Human feedback is not a product afterthought. The approval inbox and decision
log are alignment infrastructure.

**MVP action:** Capture approve/reject/revise reasons as structured data.

### 5.4 DPO - Rafailov et al. (2023)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2305.18290
- OpenReview: https://openreview.net/forum?id=HPuSIXJaa9

DPO simplifies preference optimization by avoiding a separate reward model and RL loop.

**Project takeaway:** If AMD ACT II later collects preference pairs, DPO is a plausible adaptation
method: chosen recommendation vs rejected recommendation, with the same evidence context.

**MVP action:** Preserve rejected recommendations and accepted alternatives. Do not overwrite them.

### 5.5 ORPO - Hong, Lee, Thorne (2024)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2403.07691
- ACL Anthology: https://aclanthology.org/2024.emnlp-main.626/

ORPO combines supervised fine-tuning and preference alignment without a separate reference model.

**Project takeaway:** Preference tuning is becoming simpler. The blocker is not algorithmic
availability; it is clean preference data.

**MVP action:** Store preference data cleanly now; choose ORPO/DPO later only after evals.

### 5.6 GRPO / DeepSeekMath - Shao et al. (2024)

**Primary source:** https://arxiv.org/abs/2402.03300

DeepSeekMath introduced Group Relative Policy Optimization, a PPO variant that reduces training
resource needs by estimating baselines from group scores rather than using a critic model.

**Project takeaway:** GRPO is relevant for future reasoning-model training, not the MVP. Its immediate
lesson is that automated group scoring can improve reasoning. For AMD ACT II, group scoring maps to
critic checks, simulation outputs, and human verdicts.

**MVP action:** Keep golden scenario scoring deterministic. Later, preference optimization can use
approved/rejected decision groups.

## Project Takeaways From Category 5

### A. The Approval Inbox Is Alignment Data

Every human approval, rejection, and revision should become structured learning material.

### B. Do Not Explore In Production Operations

Classic RL exploration is dangerous in business operations. AMD ACT II should recommend, simulate,
explain, and route for approval before write-back.

### C. Preference Pairs Are More Valuable Than Raw Logs

The useful data is not just "what happened." It is "given this evidence, option A was preferred over
option B because..."

### D. Reward Must Be Multi-Objective

Recovered rand matters, but so do spoilage, customer trust, stockout risk, margin, safety, and human
override frequency.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep HITL for risky actions | RLHF, DQN, PPO | Feedback is valuable; unsafe exploration is not |
| Store rejected and accepted actions | DPO, ORPO | Preference optimization needs pairs |
| Use simulation before action | RL control literature | Policies need reward estimates before decisions |
| Do not implement RL in MVP | PPO, SAC, GRPO | Training loops are out of scope and risky |
| Track outcomes after approval | RLHF, DPO | Alignment improves only with outcome data |

## What We Are Not Using Yet

- No live reinforcement learning.
- No autonomous exploration.
- No policy-gradient training.
- No reward model.
- No DPO/ORPO until real preference data exists.

## Category 5 Source List

- Mnih et al., "Human-level control through deep reinforcement learning" (2015):
  https://www.nature.com/articles/nature14236
- Schulman et al., "Trust Region Policy Optimization" (2015):
  https://arxiv.org/abs/1502.05477
- Schulman et al., "Proximal Policy Optimization Algorithms" (2017):
  https://arxiv.org/abs/1707.06347
- Haarnoja et al., "Soft Actor-Critic" (2018):
  https://arxiv.org/abs/1801.01290
- Ouyang et al., "Training language models to follow instructions with human feedback" (2022):
  https://arxiv.org/abs/2203.02155
- Rafailov et al., "Direct Preference Optimization" (2023):
  https://arxiv.org/abs/2305.18290
- Hong, Lee, Thorne, "ORPO" (2024):
  https://arxiv.org/abs/2403.07691
- Shao et al., "DeepSeekMath" / GRPO (2024):
  https://arxiv.org/abs/2402.03300

---

# 6. Multi-Agent Systems

## Why This Category Matters

AMD ACT II is explicitly a multi-agent operations OS. This category is direct architecture research.
The important warning is that multi-agent systems can amplify errors just as easily as they distribute
work. The MVP should therefore use a deterministic orchestrator, a small role set, shared contracts,
and a Critic, not a free-form chatroom of agents.

## Selected Papers And Systems

### 6.1 ReAct - Yao et al. (2022)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2210.03629
- Google Research blog: https://research.google/blog/react-synergizing-reasoning-and-acting-in-language-models/

ReAct interleaves reasoning and actions so a model can decide, call tools, observe results, and
continue.

**Project takeaway:** AMD ACT II agents should not invent facts. They should call tools, inspect
source-linked data, and produce evidence-backed actions.

**MVP action:** Use tool outputs and evidence objects as the visible trace. Do not expose hidden
chain-of-thought as the product explanation.

### 6.2 CAMEL - Li et al. (2023)

**Primary source:** https://arxiv.org/abs/2303.17760

CAMEL explores role-playing agents and communicative cooperation.

**Project takeaway:** Roles help, but role-play alone is not enough for business reliability. AMD ACT
II roles must be bounded by contracts and SOPs.

**MVP action:** Keep agent prompts role-specific but output-schema identical.

### 6.3 Reflexion - Shinn et al. (2023)

**Primary source:** https://arxiv.org/abs/2303.11366

Reflexion uses verbal feedback and episodic memory instead of weight updates to improve future
trials.

**Project takeaway:** This maps directly to visible learning. AMD ACT II can learn from outcomes by
updating thresholds, notes, or patterns without training model weights.

**MVP action:** Keep the visible learning moment and log the memory update.

### 6.4 Voyager - Wang et al. (2023)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2305.16291
- project page: https://voyager.minedojo.org/

Voyager combines curriculum, skill library, and iterative prompting in an embodied environment.

**Project takeaway:** The useful pattern is the skill library. AMD ACT II's version is a library of
approved action patterns, thresholds, and playbooks by SKU/store/category.

**MVP action:** Do not build a full skill library yet; preserve decisions so one can emerge.

### 6.5 MetaGPT - Hong et al. (2023)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2308.00352
- OpenReview: https://openreview.net/forum?id=VtmBAGCN7o

MetaGPT encodes SOPs into prompts and assigns roles in an assembly-line workflow to reduce cascading
hallucination.

**Project takeaway:** This is one of the strongest validations of our architecture: SOPs, role
boundaries, intermediate verification, and structured handoffs.

**MVP action:** Keep the cascade deterministic: Inventory -> Expiry -> Demand -> Opportunity ->
Simulation -> Executive -> Critic.

### 6.6 AutoGen - Wu et al. (2023)

**Primary and official sources:**
- arXiv: https://arxiv.org/abs/2308.08155
- Microsoft Research: https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/

AutoGen is a framework for conversable agents that can combine LLMs, tools, and human input.

**Project takeaway:** Human-in-the-loop and tool use are core multi-agent concepts, but the MVP should
not import a whole framework unless it simplifies the slice. FastAPI plus deterministic orchestrator
is already locked.

**MVP action:** Learn from AutoGen's patterns, but keep the modular monolith and custom orchestrator.

### 6.7 AgentVerse - Chen et al. (2023)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2308.10848
- OpenReview: https://openreview.net/forum?id=EHg5GDnyq1

AgentVerse explores dynamic multi-agent collaboration and emergent behaviors.

**Project takeaway:** More agents can help, but emergent behavior is a risk. AMD ACT II should avoid
dynamic agent composition until the core spine is solid.

**MVP action:** Keep 5-agent spine full and stub the rest.

## Project Takeaways From Category 6

### A. Multi-Agent Does Not Mean Agent Chatroom

The reliable pattern is an orchestrated assembly line with contracts, not unbounded agent debate.

### B. SOPs Beat Personality

Agent roles should encode operational responsibilities, policies, and output contracts. "You are an
expert" is weaker than a clear SOP.

### C. The Critic Is Necessary

Multi-agent cascades can amplify hallucinations. A Critic gate is not decoration; it is the control
surface.

### D. Memory Should Store Outcomes, Not Agent Chatter

The reusable knowledge is approved actions, rejected actions, thresholds, evidence, and outcomes.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Use deterministic orchestrator | MetaGPT, AutoGen | Reliable workflows need programmed coordination |
| Keep small spine | AgentVerse, CAMEL | More agents increase coordination risk |
| Use shared evidence contract | ReAct, MetaGPT | Tool outputs and handoffs must be auditable |
| Keep Critic after Executive | MetaGPT, Reflexion | Intermediate verification reduces cascading errors |
| Store learning as memory updates | Reflexion, Voyager | Weight updates are unnecessary for MVP learning |

## What We Are Not Using Yet

- No autonomous agent society.
- No dynamic role spawning.
- No all-agent debate.
- No AutoGPT-style unattended autonomy.
- No framework migration away from locked FastAPI/orchestrator design.

## Category 6 Source List

- Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" (2022):
  https://arxiv.org/abs/2210.03629
- Li et al., "CAMEL" (2023):
  https://arxiv.org/abs/2303.17760
- Shinn et al., "Reflexion" (2023):
  https://arxiv.org/abs/2303.11366
- Wang et al., "Voyager" (2023):
  https://arxiv.org/abs/2305.16291
- Hong et al., "MetaGPT" (2023):
  https://arxiv.org/abs/2308.00352
- Wu et al., "AutoGen" (2023):
  https://arxiv.org/abs/2308.08155
- Chen et al., "AgentVerse" (2023):
  https://arxiv.org/abs/2308.10848

---

# 7. Reasoning Models

## Why This Category Matters

Reasoning research is directly relevant to Executive decisions, Critic review, simulation checking,
and evidence reconciliation. But the MVP should distinguish between **internal reasoning** and
**user-facing explanation**. Users need auditable evidence and decisions, not private chain-of-thought.

## Selected Papers And Methods

### 7.1 Chain-of-Thought And Zero-Shot CoT - Wei et al. (2022), Kojima et al. (2022)

**Primary sources:**
- Chain-of-Thought: https://arxiv.org/abs/2201.11903
- Zero-Shot CoT: https://arxiv.org/abs/2205.11916

CoT showed that intermediate reasoning can improve complex reasoning. Zero-Shot CoT showed simple
reasoning prompts can unlock reasoning behavior without examples.

**Project takeaway:** Asking models to reason can improve outputs, but the product explanation should
be structured evidence, not raw thought traces.

**MVP action:** Prompt agents to analyze carefully, but output only schema fields, evidence, and concise
rationale.

### 7.2 Self-Consistency - Wang et al. (2022)

**Primary source:** https://arxiv.org/abs/2203.11171

Self-consistency samples multiple reasoning paths and selects the most consistent answer.

**Project takeaway:** Useful for high-risk decisions, but expensive. AMD ACT II can use a cheaper
variant: multiple agents plus critic consistency checks.

**MVP action:** Do not sample many completions by default. Use critic review for reliability.

### 7.3 Least-to-Most Prompting - Zhou et al. (2022)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2205.10625
- OpenReview: https://openreview.net/forum?id=WZH7099tgfM

Least-to-most prompting decomposes a complex problem into simpler subproblems and solves them in
sequence.

**Project takeaway:** This exactly matches the cascade design. Inventory, expiry, demand,
opportunity, and simulation are subproblems leading to an executive decision.

**MVP action:** Keep the cascade decomposition. Do not collapse all reasoning into one mega-agent.

### 7.4 Program-Aided / Program-of-Thoughts - Gao et al. (2022), Chen et al. (2022)

**Primary sources:**
- PAL: https://arxiv.org/abs/2211.10435
- Program of Thoughts: https://arxiv.org/abs/2211.12588

These methods offload computation to executable programs instead of relying on the LLM to calculate.

**Project takeaway:** Critical. Rand impact, markdown math, units cleared, and inventory projections
should be deterministic Python/service calculations, not model arithmetic.

**MVP action:** Simulation agent should call deterministic tools. The LLM explains and selects, but
the system computes.

### 7.5 Tree Of Thoughts And Graph Of Thoughts - Yao et al. (2023), Besta et al. (2023)

**Primary sources:**
- Tree of Thoughts: https://arxiv.org/abs/2305.10601
- Graph of Thoughts: https://arxiv.org/abs/2308.09687

These approaches explore multiple reasoning paths or arbitrary dependency graphs of thoughts.

**Project takeaway:** Useful inspiration for roadmap Detective/root-cause analysis, but too expensive
for the live MVP cascade unless scoped to high-risk review.

**MVP action:** Do not implement ToT/GoT search. Use deterministic agent stages and critic gate.

### 7.6 Self-Refine And Reflexion - Madaan et al. (2023), Shinn et al. (2023)

**Primary sources:**
- Self-Refine: https://arxiv.org/abs/2303.17651
- Reflexion: https://arxiv.org/abs/2303.11366

Both show test-time or memory-based improvement through feedback/refinement without weight updates.

**Project takeaway:** AMD ACT II's validation retry and Critic revision flow are practical, bounded
versions of refinement. The important rule is to bound retries so latency and cost do not explode.

**MVP action:** Keep one structured retry after schema validation failure. Keep Critic revise/reject.

## Project Takeaways From Category 7

### A. Reasoning Must Be Grounded

Reasoning without source refs can produce plausible nonsense. Every conclusion must connect to facts.

### B. Compute With Tools

Program-aided reasoning strongly supports deterministic simulation. Never trust an LLM with rand math
when a tool can compute it.

### C. Decomposition Is The Architecture

Least-to-most reasoning supports the multi-agent cascade. Each agent owns one smaller question.

### D. Reflection Needs Budgets

Self-refine loops can improve outputs but can also inflate latency. AMD ACT II should use bounded
retry/critic loops.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Use agent cascade decomposition | Least-to-most, ToT | Smaller subproblems are more reliable |
| Use deterministic simulation tools | PAL, PoT | LLM arithmetic is not enough for ZAR decisions |
| Keep Critic and validation retry | Self-Refine, Reflexion | Bounded refinement improves reliability |
| Do not expose raw chain-of-thought | CoT literature, safety practice | Users need evidence and rationale, not private thought traces |
| Avoid expensive search by default | ToT, GoT, self-consistency | Live demo needs predictable latency |

## What We Are Not Using Yet

- No Tree-of-Thought search loop.
- No Graph-of-Thought reasoning engine.
- No unbounded self-refinement.
- No raw hidden reasoning in the UI.
- No LLM-only financial math.

## Category 7 Source List

- Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (2022):
  https://arxiv.org/abs/2201.11903
- Wang et al., "Self-Consistency Improves Chain of Thought Reasoning" (2022):
  https://arxiv.org/abs/2203.11171
- Zhou et al., "Least-to-Most Prompting" (2022):
  https://arxiv.org/abs/2205.10625
- Kojima et al., "Large Language Models are Zero-Shot Reasoners" (2022):
  https://arxiv.org/abs/2205.11916
- Gao et al., "PAL: Program-aided Language Models" (2022):
  https://arxiv.org/abs/2211.10435
- Chen et al., "Program of Thoughts Prompting" (2022):
  https://arxiv.org/abs/2211.12588
- Madaan et al., "Self-Refine" (2023):
  https://arxiv.org/abs/2303.17651
- Yao et al., "Tree of Thoughts" (2023):
  https://arxiv.org/abs/2305.10601
- Besta et al., "Graph of Thoughts" (2023):
  https://arxiv.org/abs/2308.09687
- Shinn et al., "Reflexion" (2023):
  https://arxiv.org/abs/2303.11366

---

# 8. Retrieval-Augmented Generation

## Why This Category Matters

RAG is direct MVP architecture. AMD ACT II must answer questions and recommend actions using current
store/product/decision data. Model weights cannot contain today's stock counts, expiry dates, sales
velocity, or human approvals. RAG is how we keep the model grounded and updateable.

The core product rule:

**The model may reason over retrieved facts, but the system must own retrieval, provenance, and
freshness.**

## Selected Papers And Methods

### 8.1 REALM And Original RAG - Guu et al. (2020), Lewis et al. (2020)

**Primary sources:**
- REALM: https://arxiv.org/abs/2002.08909
- RAG: https://arxiv.org/abs/2005.11401

REALM and RAG showed the value of explicit retrievable memory over relying only on parametric model
knowledge. RAG also emphasizes provenance and updatable world knowledge.

**Project takeaway:** AMD ACT II should never ask the model to remember operational facts. Facts live
in Postgres/pgvector and enter prompts with source refs.

**MVP action:** RAG records must include tenant/store/SKU scope, timestamp, source, and confidence.

### 8.2 RETRO And Atlas - Borgeaud et al. (2021), Izacard et al. (2022)

**Primary sources:**
- RETRO: https://arxiv.org/abs/2112.04426
- Atlas: https://arxiv.org/abs/2208.03299

RETRO and Atlas show that retrieval can reduce parameter needs and improve knowledge-intensive
performance. Atlas also studies updateable indexes and few-shot use.

**Project takeaway:** Retrieval lets smaller models act smarter because they do not need to store all
business facts in weights.

**MVP action:** Prefer smaller/mid model plus strong retrieval before jumping to huge model.

### 8.3 Self-RAG - Asai et al. (2023)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2310.11511
- project page: https://selfrag.github.io/

Self-RAG trains models to retrieve, generate, and critique through self-reflection.

**Project takeaway:** The architecture equivalent is explicit: retrieve only when needed, judge
retrieval relevance, generate with citations, then Critic checks evidence.

**MVP action:** Add retrieval relevance/evidence sufficiency checks to Critic behavior.

### 8.4 Corrective RAG - Yan et al. (2024)

**Primary source:** https://arxiv.org/abs/2401.15884

CRAG evaluates retrieved document quality and triggers corrective actions when retrieval is poor.

**Project takeaway:** Bad retrieval is dangerous because it gives the model bad confidence. AMD ACT II
needs "no sufficient evidence" as a valid outcome.

**MVP action:** If retrieval is weak, agents should recommend `monitor` or require human review rather
than inventing a confident action.

### 8.5 RAPTOR - Sarthi et al. (2024)

**Primary source:** https://arxiv.org/abs/2401.18059

RAPTOR builds hierarchical summaries for retrieval at multiple abstraction levels.

**Project takeaway:** Useful roadmap idea for long decision histories. For MVP, use simpler per-SKU
memory summaries.

**MVP action:** Keep memory summary small: recent decisions, threshold, last outcome, risk notes.

### 8.6 GraphRAG - Edge et al. / Microsoft (2024)

**Primary sources:**
- arXiv: https://arxiv.org/abs/2404.16130
- Microsoft Research publications: https://www.microsoft.com/en-us/research/project/graphrag/publications/

GraphRAG builds graph-based indexes and community summaries for global questions over private
corpora.

**Project takeaway:** Highly relevant roadmap for Detective/root-cause analysis, supplier networks,
and "why is this happening across stores?" But it is not needed for the hackathon MVP.

**MVP action:** Use Postgres/pgvector now. Defer graph/GraphRAG to roadmap unless core cascade is
already flawless.

## Project Takeaways From Category 8

### A. RAG Is The Evidence Layer

RAG should return auditable facts, not just text snippets. Every retrieved item needs source,
timestamp, and scope.

### B. Retrieval Can Fail

RAG systems need a "retrieval insufficient" state. Bad context is worse than no context.

### C. Small Models Plus Good Retrieval Are A Serious Default

RETRO/Atlas support a cost-efficient pattern: do not use huge models to compensate for weak data
access.

### D. GraphRAG Is Roadmap Detective Material

GraphRAG is promising for cross-store/supplier/root-cause questions, but it is not MVP-critical.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Use Postgres plus pgvector | RAG, REALM, Atlas | External memory must be updateable and scoped |
| Require source refs in evidence | RAG, Self-RAG | Provenance is central to trust |
| Add retrieval sufficiency checks | CRAG, Self-RAG | Bad retrieval should not produce confident actions |
| Keep memory summaries compact | RAPTOR, Transformer-XL | Long history needs abstraction |
| Defer graph DB | GraphRAG | Roadmap value, not MVP necessity |

## What We Are Not Using Yet

- No dedicated graph database.
- No full GraphRAG pipeline.
- No web search in the operational demo unless explicitly mocked.
- No retrieval without source metadata.
- No dumping raw retrieved rows into prompts.

## Category 8 Source List

- Guu et al., "REALM" (2020):
  https://arxiv.org/abs/2002.08909
- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (2020):
  https://arxiv.org/abs/2005.11401
- Borgeaud et al., "Improving language models by retrieving from trillions of tokens" / RETRO (2021):
  https://arxiv.org/abs/2112.04426
- Izacard et al., "Atlas: Few-shot Learning with Retrieval Augmented Language Models" (2022):
  https://arxiv.org/abs/2208.03299
- Asai et al., "Self-RAG" (2023):
  https://arxiv.org/abs/2310.11511
- Yan et al., "Corrective Retrieval Augmented Generation" (2024):
  https://arxiv.org/abs/2401.15884
- Sarthi et al., "RAPTOR" (2024):
  https://arxiv.org/abs/2401.18059
- Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (2024):
  https://arxiv.org/abs/2404.16130

---

# 9. Vector Databases And Search

## Why This Category Matters

Vector search is direct MVP architecture because AMD ACT II needs retrieval over product records,
events, decisions, policies, and learned patterns. The system is not just "LLM plus database"; it is
an evidence retrieval system that feeds agents with scoped, fresh, auditable facts.

The build decision already points to **Postgres plus pgvector**, not a separate vector database. This
category validates that choice for the hackathon and clarifies when a dedicated vector DB would become
worth it.

## Selected Papers And Systems

### 9.1 FAISS - Johnson, Douze, Jegou (2017)

**Primary source:** https://arxiv.org/abs/1702.08734

FAISS shows how billion-scale similarity search can be made practical with GPU-optimized k-selection
and compressed vector search.

**Project takeaway:** Useful as the high-scale north star, not an MVP dependency. AMD ACT II's
retrieval volume is tiny compared with FAISS-scale workloads. The lesson is to measure recall/latency
and choose the simplest index that works.

**MVP action:** Do not add FAISS unless pgvector cannot hit retrieval needs.

### 9.2 HNSW - Malkov, Yashunin (2016/2020)

**Primary sources:**
- arXiv: https://arxiv.org/abs/1603.09320
- IEEE/TPAMI: https://dl.acm.org/doi/10.1109/TPAMI.2018.2889473

HNSW uses a layered navigable small-world graph to trade exactness for very fast approximate nearest
neighbor retrieval.

**Project takeaway:** HNSW is the default candidate when semantic retrieval grows beyond exact scan.
It is especially useful for low-latency RAG over decision memory and policy fragments.

**MVP action:** Start with pgvector exact search or HNSW depending on dataset size. Log retrieval
scores and source ids so bad matches are visible.

### 9.3 ScaNN - Guo et al. / Google Research (2020)

**Primary and official sources:**
- Google Research announcement: https://research.google/blog/announcing-scann-efficient-vector-similarity-search/
- Milvus docs summary of ScaNN-style indexing: https://milvus.io/docs/index.md

ScaNN combines partitioning, asymmetric hashing, and optimized distance computation for efficient
large-scale vector search.

**Project takeaway:** ScaNN reinforces the speed/recall tradeoff, but it does not change our MVP
architecture. It is useful background if retrieval later becomes a dedicated service.

**MVP action:** Do not introduce ScaNN now.

### 9.4 pgvector - Official Postgres Extension

**Official sources:**
- pgvector GitHub: https://github.com/pgvector/pgvector
- PostgreSQL release note for pgvector 0.8.0: https://www.postgresql.org/about/news/pgvector-080-released-2952/

pgvector adds vector similarity search to Postgres and supports exact search plus approximate indexes
such as HNSW and IVFFlat.

**Project takeaway:** This is the right MVP choice because the app already needs Postgres for
transactional state, approvals, decisions, and traces. Keeping embeddings beside structured metadata
makes filtering by tenant/store/SKU/time straightforward.

**MVP action:** Store embeddings with metadata fields, not as anonymous chunks:

- `tenant_id`
- `store_id`
- `sku`
- `record_type`
- `source_ref`
- `created_at`
- `valid_from`
- `confidence`
- `embedding_model`

### 9.5 Dedicated Vector Databases - Milvus, Qdrant, Chroma, Elasticsearch

**Official sources:**
- Milvus index docs: https://milvus.io/docs/index-explained.md
- Qdrant indexing docs: https://qdrant.tech/documentation/manage-data/indexing/
- Chroma docs: https://docs.trychroma.com/docs/overview/introduction
- Elasticsearch dense vector docs: https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/dense-vector

These systems are useful when vector search becomes a specialized production concern: large data,
complex filtering, distributed operations, high write volume, or hybrid sparse/dense search at scale.

**Project takeaway:** They are roadmap options. They should not be pulled into the hackathon unless
pgvector blocks a core demo path.

**MVP action:** Keep a repository interface around retrieval so a future vector backend can be swapped
without rewriting agents.

## Project Takeaways From Category 9

### A. Retrieval Is A Database Problem And A Product Trust Problem

The model should not decide which facts exist. The system retrieves scoped facts, attaches source refs,
and lets agents reason only over those facts.

### B. Metadata Filtering Is As Important As Similarity

For retail operations, the best semantic match is wrong if it belongs to another tenant, store, SKU, or
time window.

### C. Start With pgvector

Postgres plus pgvector keeps the MVP simple and auditable. Dedicated vector DBs are a scaling move, not
a virtue signal.

### D. Measure Recall And Latency

HNSW/IVFFlat are speed/recall tradeoffs. Retrieval tests should include expected source ids, not just
"answer seems good."

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Use Postgres plus pgvector | pgvector, RAG, HNSW | One data plane for operational records and memory |
| Add retrieval metadata fields | Qdrant, Elasticsearch, pgvector | Filtering is required for tenant/SKU/time correctness |
| Keep retrieval behind repository/service interface | Milvus, Qdrant, Chroma | Future backend swap stays contained |
| Log source ids and scores | HNSW/ScaNN tradeoffs | Retrieval quality must be inspectable |
| Avoid dedicated vector DB in MVP | pgvector, get-shit-done | Simpler stack wins unless volume forces change |

## What We Are Not Using Yet

- No Milvus/Qdrant/Chroma production dependency.
- No FAISS service.
- No separate search cluster.
- No vector search without metadata filters.
- No RAG answer without source refs.

## Category 9 Source List

- Johnson, Douze, Jegou, "Billion-scale similarity search with GPUs" (2017):
  https://arxiv.org/abs/1702.08734
- Malkov, Yashunin, "Efficient and robust approximate nearest neighbor search using Hierarchical
  Navigable Small World graphs" (2016/2020): https://arxiv.org/abs/1603.09320
- Google Research, "Announcing ScaNN: Efficient Vector Similarity Search" (2020):
  https://research.google/blog/announcing-scann-efficient-vector-similarity-search/
- pgvector official repository: https://github.com/pgvector/pgvector
- PostgreSQL, "pgvector 0.8.0 Released" (2024):
  https://www.postgresql.org/about/news/pgvector-080-released-2952/
- Milvus index docs: https://milvus.io/docs/index-explained.md
- Qdrant indexing docs: https://qdrant.tech/documentation/manage-data/indexing/
- Chroma docs: https://docs.trychroma.com/docs/overview/introduction
- Elasticsearch dense vector docs:
  https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/dense-vector

---

# 10. GPU Training And Parallelism

## Why This Category Matters

The MVP is not training a foundation model. Still, this category matters because the hackathon has an
AMD technology story: open models served through vLLM/ROCm on MI300X, with Fireworks fallback through
the same OpenAI-compatible client. GPU systems research also teaches the discipline of measuring
throughput, memory, batching, and bottlenecks rather than making vague "AI infrastructure" claims.

## Selected Papers And Systems

### 10.1 Megatron-LM - Shoeybi et al. (2019)

**Primary source:** https://arxiv.org/abs/1909.08053

Megatron-LM demonstrates tensor/model parallelism for training multi-billion parameter Transformers.

**Project takeaway:** The direct MVP lesson is not to train with Megatron. The lesson is that model
size is a systems problem: memory, communication, parallelism, and measurement are as important as the
architecture itself.

**MVP action:** Report concrete inference metrics: model name, GPU path, tokens/sec, latency, context
size, and request trace.

### 10.2 DeepSpeed ZeRO Family - Rajbhandari et al. (2019-2021)

**Primary sources:**
- ZeRO: https://arxiv.org/abs/1910.02054
- ZeRO-Offload: https://arxiv.org/abs/2101.06840
- ZeRO-Infinity: https://arxiv.org/abs/2104.07857
- DeepSpeed official docs: https://www.deepspeed.ai/tutorials/zero/

ZeRO partitions optimizer states, gradients, and parameters to remove memory redundancy. Later work
offloads across CPU/NVMe to push model size further.

**Project takeaway:** Memory pressure is a first-class design constraint. For AMD ACT II, the
analogous serving constraint is KV cache, batch size, context length, and model precision.

**MVP action:** Keep contexts small and structured. Do not push long prompts as a substitute for
retrieval.

### 10.3 GPipe, PipeDream, Horovod, Alpa

**Primary sources:**
- GPipe: https://arxiv.org/abs/1811.06965
- PipeDream: https://arxiv.org/abs/1806.03377
- Horovod: https://arxiv.org/abs/1802.05799
- Alpa: https://arxiv.org/abs/2201.12023

These systems cover pipeline parallelism, ring-allreduce distributed training, and automated
parallelization planning.

**Project takeaway:** They belong to roadmap infrastructure, not the MVP. The useful product lesson is
interface discipline: complex distributed systems work when boundaries and communication costs are
explicit.

**MVP action:** Keep one inference gateway and one OpenAI-compatible client interface so local MI300X
and Fireworks fallback are interchangeable.

### 10.4 PyTorch FSDP And AMD ROCm/vLLM

**Official sources:**
- PyTorch FSDP docs: https://docs.pytorch.org/docs/stable/fsdp.html
- PyTorch FSDP tutorial: https://docs.pytorch.org/tutorials/intermediate/FSDP_tutorial.html
- AMD ROCm vLLM inference docs: https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference/benchmark-docker/vllm.html
- vLLM GPU/ROCm docs: https://docs.vllm.ai/en/latest/getting_started/installation/gpu/
- AMD ROCm workload optimization docs:
  https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html

FSDP is relevant for future fine-tuning; ROCm/vLLM docs are directly relevant to the hackathon proof.

**Project takeaway:** The build should make AMD inference visible and measurable, not hidden as an
implementation detail.

**MVP action:** Use the same request schema for Fireworks and vLLM. Capture a real vLLM/ROCm run if
hardware access exists; otherwise keep the local path documented and demo through fallback.

## Project Takeaways From Category 10

### A. Inference Is Also A Systems Problem

Even without training, AMD ACT II must manage model size, context length, batch behavior, and latency.

### B. The AMD Story Needs Numbers

"We use MI300X" is weak. "This model served through vLLM/ROCm on MI300X with this latency/tokens/sec"
is credible.

### C. Keep Provider Abstraction Boring

The OpenAI-compatible client is the right boundary. Agents should not care whether the model is local
vLLM or Fireworks.

### D. Training Infrastructure Is Roadmap

FSDP/DeepSpeed/QLoRA matter later. MVP value comes from reliable inference, evidence contracts, and
evaluation.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Use vLLM/ROCm proof path | AMD ROCm docs, vLLM docs | Direct AMD technology relevance |
| Keep Fireworks fallback | Provider abstraction | Demo reliability without changing agent code |
| Measure tokens/sec and latency | Megatron, ZeRO, vLLM | Systems claims need metrics |
| Do not train models in MVP | DeepSpeed/FSDP complexity | Training is not needed for hackathon value |
| Keep contexts compact | ZeRO memory lesson, attention research | Memory is a bottleneck at serving time too |

## What We Are Not Using Yet

- No distributed training cluster.
- No Megatron/DeepSpeed/FSDP training job.
- No custom ROCm kernels.
- No model-parallel implementation.
- No training as part of the live demo.

## Category 10 Source List

- Shoeybi et al., "Megatron-LM" (2019): https://arxiv.org/abs/1909.08053
- Rajbhandari et al., "ZeRO" (2019): https://arxiv.org/abs/1910.02054
- Ren et al., "ZeRO-Offload" (2021): https://arxiv.org/abs/2101.06840
- Rajbhandari et al., "ZeRO-Infinity" (2021): https://arxiv.org/abs/2104.07857
- Huang et al., "GPipe" (2018): https://arxiv.org/abs/1811.06965
- Harlap et al., "PipeDream" (2018): https://arxiv.org/abs/1806.03377
- Sergeev, Del Balso, "Horovod" (2018): https://arxiv.org/abs/1802.05799
- Zheng et al., "Alpa" (2022): https://arxiv.org/abs/2201.12023
- PyTorch FSDP docs: https://docs.pytorch.org/docs/stable/fsdp.html
- AMD ROCm vLLM inference docs:
  https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference/benchmark-docker/vllm.html
- vLLM GPU/ROCm docs: https://docs.vllm.ai/en/latest/getting_started/installation/gpu/

---

# 11. Model Compression

## Why This Category Matters

Compression is directly relevant to serving cost, latency, and GPU memory. For AMD ACT II, the main
question is not "can we compress a model?" It is "does the compressed model still produce reliable
schema-valid, evidence-grounded business decisions?"

## Selected Papers And Methods

### 11.1 Knowledge Distillation - Hinton, Vinyals, Dean (2015)

**Primary source:** https://arxiv.org/abs/1503.02531

Distillation transfers behavior from larger teacher models or ensembles into a smaller student model.

**Project takeaway:** Strong roadmap idea. If Executive/Critic need a larger model but routine agents
do not, we can later distill repeated decisions into smaller specialized models or prompts.

**MVP action:** Store input/output/evidence/outcome records cleanly so distillation is possible later.

### 11.2 LLM.int8 - Dettmers et al. (2022)

**Primary source:** https://arxiv.org/abs/2208.07339

LLM.int8 reduces inference memory while preserving important outlier dimensions in higher precision.

**Project takeaway:** Compression can unlock larger local models, but it must be tested on our schema
and reasoning tasks.

**MVP action:** Treat quantized model choice as an eval result, not an assumption.

### 11.3 GPTQ, AWQ, SmoothQuant

**Primary sources:**
- GPTQ: https://arxiv.org/abs/2210.17323
- AWQ: https://arxiv.org/abs/2306.00978
- SmoothQuant: https://arxiv.org/abs/2211.10438

These post-training quantization methods reduce model memory and can improve serving feasibility.
GPTQ focuses on one-shot weight quantization; AWQ protects activation-important channels; SmoothQuant
migrates activation quantization difficulty into weights for efficient INT8 serving.

**Project takeaway:** Quantization is a likely practical lever for MI300X/vLLM serving, especially for
keeping several candidate models available. The risk is silent behavior degradation: broken JSON,
weaker evidence use, or more hallucinated actions.

**MVP action:** If using a quantized model, run the golden scenario and schema-validity checks against
the quantized artifact, not just the base model.

### 11.4 SparseGPT And Pruning

**Primary sources:**
- SparseGPT: https://arxiv.org/abs/2301.00774
- Lottery Ticket Hypothesis: https://arxiv.org/abs/1803.03635
- Pruning/quantization survey: https://arxiv.org/abs/2101.09671

Pruning removes weights or structures to reduce computation. SparseGPT showed one-shot pruning can
work on massive GPT-family models, but real speedups depend on hardware and sparsity structure.

**Project takeaway:** Interesting roadmap, less practical than quantization for the MVP.

**MVP action:** Do not prune models for hackathon. Use available model artifacts.

## Project Takeaways From Category 11

### A. Compression Is A Serving Tool, Not A Quality Guarantee

A smaller/faster model is only good if it passes AMD ACT II's evidence, JSON, and decision tests.

### B. Quantization Needs Product Evals

Generic perplexity or benchmark scores are not enough. We need:

- schema validity
- evidence citation correctness
- action accuracy
- hallucination rate
- latency
- cost/GPU memory

### C. Distillation Starts With Data Hygiene

Future distillation depends on clean logs now: prompt version, model id, evidence ids, human decision,
and outcome.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep model card per candidate | Quantization/distillation methods | Runtime behavior depends on artifact details |
| Run golden scenario per model artifact | GPTQ, AWQ, SmoothQuant | Compression can change behavior |
| Store decision/outcome data | Distillation | Future smaller models need clean examples |
| Do not prune in MVP | SparseGPT complexity | Low value versus available quantized artifacts |
| Measure latency and memory | LLM.int8, SmoothQuant | Serving efficiency is the point |

## What We Are Not Using Yet

- No custom quantization pipeline.
- No pruning pipeline.
- No distillation training run.
- No compressed model without eval.
- No assumption that smaller is automatically better.

## Category 11 Source List

- Hinton, Vinyals, Dean, "Distilling the Knowledge in a Neural Network" (2015):
  https://arxiv.org/abs/1503.02531
- Dettmers et al., "LLM.int8()" (2022): https://arxiv.org/abs/2208.07339
- Frantar et al., "GPTQ" (2022): https://arxiv.org/abs/2210.17323
- Lin et al., "AWQ" (2023): https://arxiv.org/abs/2306.00978
- Xiao et al., "SmoothQuant" (2022): https://arxiv.org/abs/2211.10438
- Frantar, Alistarh, "SparseGPT" (2023): https://arxiv.org/abs/2301.00774
- Frankle, Carbin, "The Lottery Ticket Hypothesis" (2018): https://arxiv.org/abs/1803.03635
- Liang et al., "Pruning and Quantization for Deep Neural Network Acceleration: A Survey" (2021):
  https://arxiv.org/abs/2101.09671

---

# 12. Multimodal AI

## Why This Category Matters

The MVP can simulate a scan, but the roadmap clearly points toward real shelf/product/document inputs.
Multimodal research tells us how to avoid overbuilding vision now while preserving the right interfaces
for scanner, photo evidence, invoice images, shelf state, and product compliance checks later.

## Selected Papers And Systems

### 12.1 CLIP - Radford et al. (2021)

**Primary source:** https://arxiv.org/abs/2103.00020

CLIP learns image-text representations from natural language supervision and transfers zero-shot to
many vision tasks.

**Project takeaway:** Product images can become searchable evidence. CLIP-style embeddings are useful
for matching shelf/product images to text labels, planograms, or SKU metadata.

**MVP action:** Do not build image embeddings now. Keep `SourceRef` flexible enough to point to an
image or document later.

### 12.2 Flamingo, BLIP, BLIP-2

**Primary sources:**
- Flamingo: https://arxiv.org/abs/2204.14198
- BLIP: https://arxiv.org/abs/2201.12086
- BLIP-2: https://arxiv.org/abs/2301.12597

These systems bridge vision encoders and language models, often using frozen components to reduce
training cost.

**Project takeaway:** The practical roadmap is to compose pretrained vision and language models, not
train multimodal systems from scratch.

**MVP action:** Future scanner should call a model/tool and return structured evidence; it should not
dump raw image interpretation into the agent prompt.

### 12.3 LLaVA, Qwen-VL, Kosmos-1

**Primary and project sources:**
- LLaVA / Visual Instruction Tuning: https://arxiv.org/abs/2304.08485
- LLaVA project page: https://llava-vl.github.io/
- Qwen-VL: https://arxiv.org/abs/2308.12966
- Kosmos-1: https://arxiv.org/abs/2302.14045

These models show practical visual instruction following, grounding, OCR/text reading, and image-based
dialogue.

**Project takeaway:** Visual instruction models could later inspect invoices, shelf photos, expiry
labels, damaged packaging, or missing stock. They should still produce evidence objects with confidence
and source refs.

**MVP action:** Keep multimodal as a roadmap plugin/tool category, not part of the required demo path.

### 12.4 Gemini And GPT-4V System Card

**Primary/official sources:**
- Gemini technical report: https://arxiv.org/abs/2312.11805
- GPT-4V system card: https://openai.com/index/gpt-4v-system-card/

These sources are useful for safety and product design, especially around visual limitations,
evaluation, and deployment safeguards.

**Project takeaway:** Visual AI needs safety and confidence handling. In retail operations, a bad
visual read can create wrong stock actions.

**MVP action:** If visual input enters later, require human review for low confidence or high-impact
actions.

## Project Takeaways From Category 12

### A. Multimodal Is A Tool Output, Not A UI Gimmick

The scanner should produce structured facts: SKU candidates, count estimate, label date, image region,
confidence, and source image id.

### B. Images Need Provenance Too

Every visual claim should link to an image/file/source, timestamp, and store/SKU scope.

### C. Pretrained Models Are The Path

No from-scratch multimodal training. Use pretrained models, evaluate on project examples, and keep
manual override.

### D. Simulate Now, Design For Later

The MVP can demo scanner intent with simulated events while preserving interfaces for real vision.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep scan simulation fallback | BLIP/Flamingo complexity | Real vision is not required for MVP reliability |
| Use structured visual evidence later | LLaVA, Qwen-VL | Visual output must be auditable |
| Preserve image-capable SourceRef | CLIP, Kosmos | Future multimodal retrieval needs provenance |
| Require confidence/human review | GPT-4V system card | Visual models can fail in high-impact workflows |
| Do not train VLMs | BLIP-2 | Frozen/pretrained composition is cheaper and safer |

## What We Are Not Using Yet

- No live shelf CV requirement.
- No multimodal model in the critical path.
- No image generation as evidence.
- No visual claim without source image and confidence.
- No custom VLM training.

## Category 12 Source List

- Radford et al., "CLIP" (2021): https://arxiv.org/abs/2103.00020
- Alayrac et al., "Flamingo" (2022): https://arxiv.org/abs/2204.14198
- Li et al., "BLIP" (2022): https://arxiv.org/abs/2201.12086
- Li et al., "BLIP-2" (2023): https://arxiv.org/abs/2301.12597
- Liu et al., "Visual Instruction Tuning / LLaVA" (2023): https://arxiv.org/abs/2304.08485
- Bai et al., "Qwen-VL" (2023): https://arxiv.org/abs/2308.12966
- Huang et al., "Kosmos-1" (2023): https://arxiv.org/abs/2302.14045
- Gemini Team, "Gemini" (2023): https://arxiv.org/abs/2312.11805
- OpenAI, "GPT-4V(ision) System Card" (2023):
  https://openai.com/index/gpt-4v-system-card/

---

# 13. Computer Vision

## Why This Category Matters

Computer vision is roadmap-relevant for shelf scanning, product recognition, expiry label extraction,
planogram compliance, damaged goods, and visual proof. It is not required for the hackathon MVP, but
it should shape scanner/event interfaces so future real CV can plug in cleanly.

## Selected Papers And Systems

### 13.1 YOLO - Redmon et al. (2015/2016)

**Primary source:** https://arxiv.org/abs/1506.02640

YOLO frames object detection as a single real-time prediction problem.

**Project takeaway:** Real-time shelf/product detection may eventually use YOLO-family detectors or
similar modern variants. The system lesson is latency: scanning must feel operational, not academic.

**MVP action:** Do not integrate YOLO now. Keep the scan event schema compatible with bounding boxes.

### 13.2 Faster R-CNN And Mask R-CNN

**Primary sources:**
- Faster R-CNN: https://arxiv.org/abs/1506.01497
- Mask R-CNN: https://arxiv.org/abs/1703.06870

Faster R-CNN introduced efficient region proposals; Mask R-CNN adds instance masks.

**Project takeaway:** Detection and segmentation solve different business questions. "Is this product
present?" is detection. "How much shelf space does it occupy?" may need segmentation.

**MVP action:** Store optional `bbox` and `mask_ref` fields in future visual evidence design, but do
not build them yet.

### 13.3 DETR - Carion et al. (2020)

**Primary source:** https://arxiv.org/abs/2005.12872

DETR recasts object detection as set prediction with Transformers.

**Project takeaway:** Transformer-based detection connects vision with the rest of the architecture,
but does not justify adding CV now.

**MVP action:** Keep CV behind a tool interface so detector implementation can change.

### 13.4 SAM, Grounding DINO, SAM 2

**Primary and official sources:**
- Segment Anything: https://arxiv.org/abs/2304.02643
- Grounding DINO: https://arxiv.org/abs/2303.05499
- SAM 2: https://arxiv.org/abs/2408.00714
- Meta SAM 2 page: https://ai.meta.com/research/sam2/

SAM makes promptable segmentation reusable; Grounding DINO uses language-guided open-set detection;
SAM 2 extends promptable segmentation to video with streaming memory.

**Project takeaway:** This is the strongest roadmap bundle for shelf work: language-guided detection
plus promptable segmentation can support "find this SKU", "segment the shelf area", and "track stock
presence over time."

**MVP action:** Preserve the idea of visual evidence regions, but keep demo scanning deterministic.

## Project Takeaways From Category 13

### A. Scanner Output Must Be Structured

Future CV should output:

- image id
- detected object/SKU candidate
- confidence
- bounding box or region
- timestamp
- store/location
- OCR text if present
- source model/tool id

### B. Detection, Segmentation, OCR, And Reasoning Are Separate Steps

Do not ask one model to silently do everything. Each step should produce evidence that Critic can
inspect.

### C. Vision Is Roadmap, Not MVP Risk

The hackathon demo wins on the agent cascade and business decision loop. Real CV can arrive after the
core OS works.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Simulate scan for MVP | YOLO/CV integration cost | Demo reliability matters |
| Keep scanner as tool boundary | DETR, SAM, Grounding DINO | Future model choice should be swappable |
| Add visual region fields later | Mask R-CNN, SAM | Segmentation evidence needs coordinates |
| Require confidence and source image | SAM/Grounding DINO | Visual facts must be auditable |
| Separate CV from reasoning | All CV papers | Detection is not business decision-making |

## What We Are Not Using Yet

- No live shelf detector.
- No OCR pipeline.
- No planogram CV.
- No video tracking.
- No visual action without human review.

## Category 13 Source List

- Redmon et al., "You Only Look Once" (2015): https://arxiv.org/abs/1506.02640
- Ren et al., "Faster R-CNN" (2015): https://arxiv.org/abs/1506.01497
- He et al., "Mask R-CNN" (2017): https://arxiv.org/abs/1703.06870
- Carion et al., "DETR" (2020): https://arxiv.org/abs/2005.12872
- Kirillov et al., "Segment Anything" (2023): https://arxiv.org/abs/2304.02643
- Liu et al., "Grounding DINO" (2023): https://arxiv.org/abs/2303.05499
- Ravi et al., "SAM 2" (2024): https://arxiv.org/abs/2408.00714
- Meta AI SAM 2 page: https://ai.meta.com/research/sam2/

---

# 14. Image Generation

## Why This Category Matters

Image generation is not core AMD ACT II product logic. The platform should not generate synthetic
evidence for operational decisions. Still, image generation research is useful for demo assets,
future UX polish, synthetic training/test fixtures, and understanding multimodal model behavior.

The project rule is simple:

**Generated images may support presentation and simulated fixtures, but they must never masquerade as
real shelf, inventory, product, or approval evidence.**

## Selected Papers And Systems

### 14.1 VAE, GAN, StyleGAN, StyleGAN2

**Primary sources:**
- VAE: https://arxiv.org/abs/1312.6114
- GAN: https://arxiv.org/abs/1406.2661
- StyleGAN: https://arxiv.org/abs/1812.04948
- StyleGAN2: https://arxiv.org/abs/1912.04958

These papers explain latent representations, adversarial generation, controllable image synthesis, and
quality/artifact issues.

**Project takeaway:** Useful background for synthetic data and asset generation, but not part of the
business decision loop.

**MVP action:** Use generated visuals only for deck/UI/demo illustration if needed, clearly separated
from operational evidence.

### 14.2 Diffusion, Latent Diffusion, Stable Diffusion, SDXL

**Primary sources:**
- DDPM: https://arxiv.org/abs/2006.11239
- Latent Diffusion: https://arxiv.org/abs/2112.10752
- SDXL: https://arxiv.org/abs/2307.01952

Diffusion models dominate modern image generation. Latent diffusion reduces compute by operating in a
compressed latent space. SDXL improves quality, conditioning, and aspect-ratio handling.

**Project takeaway:** Generated UI backgrounds or pitch visuals can be made quickly, but any such image
must be labeled as illustrative.

**MVP action:** Do not use synthetic images as scanner test truth unless the fixture is explicitly
marked synthetic.

### 14.3 DALL-E, DALL-E 2, Imagen, FLUX

**Primary/official sources:**
- DALL-E: https://arxiv.org/abs/2102.12092
- DALL-E 2: https://arxiv.org/abs/2204.06125
- Imagen: https://arxiv.org/abs/2205.11487
- FLUX official repository: https://github.com/black-forest-labs/flux
- Black Forest Labs: https://bfl.ai/

These systems show text/image alignment, CLIP-latent conditioning, and modern high-fidelity
generation.

**Project takeaway:** The main useful lesson is prompt-to-asset iteration. It can help pitch material,
but not the production evidence chain.

**MVP action:** If demo images are generated, store them under a clear `/assets/demo-generated/` style
classification later and never mix with scanned evidence.

## Project Takeaways From Category 14

### A. Synthetic Media Must Be Labeled

Generated assets can be helpful, but trust collapses if synthetic material is confused with evidence.

### B. Image Generation Is Not The Scanner

Vision analysis and image synthesis are different tasks. The scanner should detect and extract facts,
not create them.

### C. Use For Storytelling, Not Decisions

Use generated images for pitch polish, mockups, or simulated fixtures only.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep generated media out of evidence chain | GAN/diffusion risk | Synthetic images can be mistaken for proof |
| Label simulated fixtures | DALL-E/SDXL/FLUX | Demo data must be honest |
| Do not add image generation dependency | get-shit-done | Not core to operational OS |
| Keep scanner and generation separate | CV vs generation papers | Detection is evidence; generation is media |

## What We Are Not Using Yet

- No image generation in critical path.
- No synthetic shelf photo as real evidence.
- No product recommendation based on generated image content.
- No image generator service dependency for MVP.

## Category 14 Source List

- Kingma, Welling, "Auto-Encoding Variational Bayes" (2013): https://arxiv.org/abs/1312.6114
- Goodfellow et al., "Generative Adversarial Nets" (2014): https://arxiv.org/abs/1406.2661
- Karras et al., "StyleGAN" (2018): https://arxiv.org/abs/1812.04948
- Karras et al., "StyleGAN2" (2019): https://arxiv.org/abs/1912.04958
- Ho, Jain, Abbeel, "Denoising Diffusion Probabilistic Models" (2020):
  https://arxiv.org/abs/2006.11239
- Rombach et al., "Latent Diffusion Models" (2021): https://arxiv.org/abs/2112.10752
- Podell et al., "SDXL" (2023): https://arxiv.org/abs/2307.01952
- Ramesh et al., "DALL-E" (2021): https://arxiv.org/abs/2102.12092
- Ramesh et al., "DALL-E 2" (2022): https://arxiv.org/abs/2204.06125
- Saharia et al., "Imagen" (2022): https://arxiv.org/abs/2205.11487
- Black Forest Labs FLUX repo: https://github.com/black-forest-labs/flux

---

# 15. Audio And Speech

## Why This Category Matters

Audio and speech are roadmap features for store managers, voice notes, meeting capture, approval
comments, and multilingual operations. They are not needed for the MVP cascade, but the architecture
should leave room for audio inputs to become structured events and evidence.

## Selected Papers And Systems

### 15.1 Deep Speech, wav2vec 2.0, Whisper

**Primary sources:**
- Deep Speech: https://arxiv.org/abs/1412.5567
- wav2vec 2.0: https://arxiv.org/abs/2006.11477
- Whisper: https://arxiv.org/abs/2212.04356

Deep Speech showed end-to-end speech recognition at scale. wav2vec 2.0 showed the power of
self-supervised speech representation learning. Whisper showed robust multilingual transcription from
large-scale weak supervision.

**Project takeaway:** Voice notes can later become typed, timestamped operational events. The model
should not act directly on raw speech; transcription should be reviewed or confidence-scored.

**MVP action:** No audio in critical path. If roadmap voice notes are added, convert speech to
structured `Event` candidates with source audio refs.

### 15.2 SpeechT5, AudioLM, VALL-E, Voicebox

**Primary sources:**
- SpeechT5: https://arxiv.org/abs/2110.07205
- AudioLM: https://arxiv.org/abs/2209.03143
- VALL-E: https://arxiv.org/abs/2301.02111
- Voicebox: https://arxiv.org/abs/2306.15687

These systems show unified speech/text representation and high-quality speech generation.

**Project takeaway:** Speech generation can help accessibility or demo narration, but voice cloning
and generated speech carry misuse risk.

**MVP action:** Do not clone voices or generate approvals. Human approvals must be explicit UI actions
with audit records.

### 15.3 SeamlessM4T

**Primary source:** https://arxiv.org/abs/2308.11596

SeamlessM4T supports speech/text translation across many languages and modalities.

**Project takeaway:** South African operations may eventually benefit from multilingual voice/text
translation. Translation should preserve original source text/audio and confidence metadata.

**MVP action:** Keep language/locale fields in future event sources.

## Project Takeaways From Category 15

### A. Voice Becomes Evidence Only After Transcription And Review

Raw audio is not directly actionable. It must become a structured event with source, transcript,
speaker, timestamp, and confidence.

### B. Generated Voice Is High-Risk

Never use generated speech as proof of approval. Approvals belong in the audited HITL workflow.

### C. Multilingual Support Is Roadmap-Relevant

South African retail teams may need multilingual interfaces, but this should come after the core
cascade works.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep audio out of MVP path | Whisper/SpeechT5 complexity | Not needed for hackathon value |
| Treat transcript as evidence candidate | Deep Speech, Whisper | ASR can be wrong |
| Preserve source audio refs later | wav2vec, Whisper | Auditability requires original source |
| Block voice-based approvals | VALL-E, Voicebox | Synthetic voice creates trust risk |
| Add locale fields later | SeamlessM4T | Translation needs source metadata |

## What We Are Not Using Yet

- No speech recognition in MVP.
- No text-to-speech in approval flow.
- No voice cloning.
- No audio generation.
- No translated action without source preservation.

## Category 15 Source List

- Hannun et al., "Deep Speech" (2014): https://arxiv.org/abs/1412.5567
- Baevski et al., "wav2vec 2.0" (2020): https://arxiv.org/abs/2006.11477
- Radford et al., "Whisper" (2022): https://arxiv.org/abs/2212.04356
- Ao et al., "SpeechT5" (2021): https://arxiv.org/abs/2110.07205
- Borsos et al., "AudioLM" (2022): https://arxiv.org/abs/2209.03143
- Wang et al., "VALL-E" (2023): https://arxiv.org/abs/2301.02111
- Le et al., "Voicebox" (2023): https://arxiv.org/abs/2306.15687
- Seamless Communication et al., "SeamlessM4T" (2023): https://arxiv.org/abs/2308.11596

---

# 16. MLOps And Model Management

## Why This Category Matters

This category is directly relevant. AMD ACT II needs reproducible model behavior, prompt versions,
golden scenario evals, traceability, rollback, and a clear model/runtime policy. We do not need a full
enterprise MLOps platform in the MVP, but we do need the habits.

## Selected Systems

### 16.1 MLflow, W&B, DVC

**Official sources:**
- MLflow docs: https://mlflow.org/docs/latest/
- MLflow tracking: https://mlflow.org/docs/latest/ml/tracking/
- MLflow model registry: https://mlflow.org/docs/latest/ml/model-registry/
- W&B registry docs: https://docs.wandb.ai/models/registry
- DVC docs: https://doc.dvc.org/user-guide

These systems cover experiment tracking, artifact/model versioning, lineage, registry, and data
version control.

**Project takeaway:** The MVP does not need all tools, especially if paid services are off-limits. But
it absolutely needs model/prompt/eval metadata.

**MVP action:** Create lightweight records for:

- model id
- provider/runtime
- prompt version
- schema version
- eval run id
- latency/tokens
- input evidence ids
- output decision id

### 16.2 Kubeflow, Ray, Airflow, TFX

**Official sources:**
- Kubeflow: https://www.kubeflow.org/docs/started/introduction/
- Ray: https://docs.ray.io/en/latest/data/data.html
- Apache Airflow: https://airflow.apache.org/docs/apache-airflow/stable/index.html
- TFX: https://www.tensorflow.org/tfx/guide

These are workflow, pipeline, distributed compute, and production ML orchestration tools.

**Project takeaway:** Roadmap only. The MVP modular monolith plus Redis Streams can express the demo
cascade. Introducing full orchestration now would slow the build.

**MVP action:** Keep event flow observable and replayable; defer platform orchestration.

### 16.3 Feast

**Official sources:**
- Feast docs: https://docs.feast.dev/
- Feast site: https://feast.dev/

Feature stores manage, validate, and serve ML features consistently across training and inference.

**Project takeaway:** AMD ACT II's operational facts behave like features: sales velocity, expiry risk,
stock level, prior outcomes. We do not need Feast now, but we should keep feature definitions
consistent.

**MVP action:** Define deterministic feature calculations in services, not scattered across agents.

## Project Takeaways From Category 16

### A. Version Everything That Changes Behavior

Models, prompts, schemas, retrieval indexes, eval fixtures, and thresholds all need versions.

### B. Lightweight MLOps Beats Tool Sprawl

Use simple tables/logs first. Adopt MLflow/DVC/Ray/Kubeflow only when the local process fails.

### C. Agent Evals Are Product Infrastructure

Golden scenario tests, JSON validity, evidence sufficiency, and latency should be run per model/prompt
candidate.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep model card | MLflow/W&B registry | Model behavior needs lifecycle metadata |
| Version prompts and schemas | MLflow tracking, DVC | Reproducibility requires behavior versions |
| Use golden scenario evals | MLflow eval pattern | Agent quality must be measurable |
| Avoid Kubeflow/Airflow in MVP | get-shit-done | Full pipeline orchestration is overkill |
| Keep deterministic features in services | Feast | Consistent features beat agent-side math |

## What We Are Not Using Yet

- No paid W&B dependency.
- No Kubeflow cluster.
- No Airflow DAGs.
- No Ray cluster.
- No full feature store.

## Category 16 Source List

- MLflow docs: https://mlflow.org/docs/latest/
- MLflow tracking: https://mlflow.org/docs/latest/ml/tracking/
- MLflow model registry: https://mlflow.org/docs/latest/ml/model-registry/
- W&B registry docs: https://docs.wandb.ai/models/registry
- DVC user guide: https://doc.dvc.org/user-guide
- Kubeflow introduction: https://www.kubeflow.org/docs/started/introduction/
- Ray Data docs: https://docs.ray.io/en/latest/data/data.html
- Apache Airflow docs: https://airflow.apache.org/docs/apache-airflow/stable/index.html
- Feast docs: https://docs.feast.dev/
- TFX guide: https://www.tensorflow.org/tfx/guide

---

# 17. AI Safety And Alignment

## Why This Category Matters

AMD ACT II recommends operational actions that affect stock, margin, waste, workload, and customer
availability. It must be useful without becoming overconfident. Safety here is less about generic chat
toxicity and more about grounded business action: no unsupported claims, no fake approvals, no hidden
autonomy, no unsafe routing, no hallucinated evidence.

## Selected Papers And Frameworks

### 17.1 RLHF, DPO, Constitutional AI

**Primary sources:**
- InstructGPT/RLHF: https://arxiv.org/abs/2203.02155
- DPO: https://arxiv.org/abs/2305.18290
- Constitutional AI: https://arxiv.org/abs/2212.08073

These works show that model behavior can be steered with demonstrations, preferences, and explicit
principles.

**Project takeaway:** AMD ACT II should have its own operating principles for agents and the Critic:
ground claims, cite sources, prefer monitor when evidence is weak, require human approval for actions,
and never fabricate operational facts.

**MVP action:** Put these principles into agent prompts and Critic rules now; collect human
approve/reject decisions as future preference data.

### 17.2 Red Teaming And Truthfulness

**Primary sources:**
- Red Teaming Language Models: https://arxiv.org/abs/2209.07858
- TruthfulQA: https://arxiv.org/abs/2109.07958

Red teaming finds failure modes before users do. TruthfulQA shows that bigger models can still imitate
falsehoods.

**Project takeaway:** The test suite needs adversarial retail cases: missing source refs, contradictory
expiry/sales data, stale inventory, impossible markdown math, and prompt injection in notes.

**MVP action:** Add red-team cases to golden scenario docs before implementation.

### 17.3 Model Cards, Datasheets, Llama Guard

**Primary sources:**
- Model Cards: https://arxiv.org/abs/1810.03993
- Datasheets for Datasets: https://arxiv.org/abs/1803.09010
- Llama Guard: https://arxiv.org/abs/2312.06674

Model/data documentation and safeguards make AI systems more governable.

**Project takeaway:** AMD ACT II needs model cards for candidate LLMs and datasheets for synthetic demo
data. Safeguard classifiers are optional, but the concept of a risk taxonomy is useful for action
routing.

**MVP action:** Use a simple action-risk taxonomy:

- informational
- monitor
- draft action
- manager approval required
- blocked / insufficient evidence

## Project Takeaways From Category 17

### A. Alignment Is A Product Workflow

HITL, Critic review, audit logs, and approvals are alignment mechanisms, not just UI features.

### B. "No Sufficient Evidence" Is A Safe Output

The model must be allowed to abstain instead of forcing an action.

### C. Red Team The Business Logic

Prompt injection, stale data, contradictory records, and wrong units are more relevant than generic
chatbot jailbreak examples.

### D. Document Model And Data Limits

Model cards and dataset datasheets belong in the project docs as soon as model candidates and demo
fixtures exist.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep Critic gate | RLHF, Constitutional AI | Behavioral rules need enforcement |
| Keep HITL approvals | RLHF/preference learning | Human feedback is both safety and future training data |
| Add adversarial evals | Red teaming, TruthfulQA | Safety failures should be discovered early |
| Add model/data cards | Model Cards, Datasheets | Governance requires documentation |
| Use action-risk taxonomy | Llama Guard | Routing needs explicit risk categories |

## What We Are Not Using Yet

- No autonomous action execution.
- No RLHF/DPO training run.
- No safety classifier dependency unless needed.
- No unreviewed high-impact recommendation.
- No answer that hides weak evidence.

## Category 17 Source List

- Ouyang et al., "Training language models to follow instructions with human feedback" (2022):
  https://arxiv.org/abs/2203.02155
- Rafailov et al., "Direct Preference Optimization" (2023): https://arxiv.org/abs/2305.18290
- Bai et al., "Constitutional AI" (2022): https://arxiv.org/abs/2212.08073
- Ganguli et al., "Red Teaming Language Models to Reduce Harms" (2022):
  https://arxiv.org/abs/2209.07858
- Lin, Hilton, Evans, "TruthfulQA" (2021): https://arxiv.org/abs/2109.07958
- Mitchell et al., "Model Cards for Model Reporting" (2018): https://arxiv.org/abs/1810.03993
- Gebru et al., "Datasheets for Datasets" (2018): https://arxiv.org/abs/1803.09010
- Inan et al., "Llama Guard" (2023): https://arxiv.org/abs/2312.06674

---

# 18. Memory Systems

## Why This Category Matters

Memory is direct architecture for AMD ACT II. The system must remember previous decisions, outcomes,
thresholds, rejected actions, and learned patterns. But memory must be disciplined: we want durable
business facts, not endless agent chatter.

## Selected Papers And Systems

### 18.1 Neural Turing Machines And Differentiable Neural Computers

**Primary sources:**
- Neural Turing Machines: https://arxiv.org/abs/1410.5401
- Differentiable Neural Computer / Nature: https://www.nature.com/articles/nature20101
- DeepMind DNC explainer: https://deepmind.google/blog/differentiable-neural-computers/

These systems connect neural controllers with external memory.

**Project takeaway:** The important idea is separation of computation and memory. AMD ACT II should
not rely on the LLM context window as the only memory.

**MVP action:** Store operational memory externally in Postgres/pgvector, not inside prompts.

### 18.2 MemGPT

**Primary sources:**
- arXiv: https://arxiv.org/abs/2310.08560
- project page: https://research.memgpt.ai/

MemGPT manages memory tiers inspired by operating-system virtual memory.

**Project takeaway:** This strongly validates the project's memory architecture. Use tiers:

- short context for current event
- recent decision summary
- long-term decision log
- semantic retrieval over patterns

**MVP action:** Keep memory summaries compact and scoped by SKU/store.

### 18.3 Generative Agents, Reflexion, Voyager

**Primary sources:**
- Generative Agents: https://arxiv.org/abs/2304.03442
- Reflexion: https://arxiv.org/abs/2303.11366
- Voyager: https://arxiv.org/abs/2305.16291

These agent systems use observation, memory, reflection, planning, and skill libraries.

**Project takeaway:** The useful memory is not raw transcript. It is selected observations,
reflections, and reusable skills/patterns. For AMD ACT II, that means approved action patterns,
threshold adjustments, repeated stock risks, and post-action outcomes.

**MVP action:** After a human approval/rejection, write a clear learning record:

- what was proposed
- evidence used
- decision made
- outcome if known
- what threshold/pattern changed

## Project Takeaways From Category 18

### A. Memory Is External And Typed

The durable memory layer should store decisions, facts, policies, and outcomes with schemas.

### B. Summaries Beat Raw Logs

Agents need compact memory summaries, not huge transcripts.

### C. Learning Without Training Is Enough For MVP

Visible learning can update thresholds, notes, and recommended actions without changing model weights.

### D. Memory Needs Forgetting And Scope

Old or irrelevant decisions should not pollute current recommendations. Scope by tenant/store/SKU/time.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Store memory in Postgres/pgvector | NTM, DNC, MemGPT | External memory beats context stuffing |
| Use SKU/store scoped summaries | MemGPT | Tiered memory keeps prompts compact |
| Store decisions and outcomes | Reflexion, Generative Agents | Learning needs experience records |
| Avoid agent transcript memory | Generative Agents lessons | Raw chatter is noisy |
| Use visible learning moment | Reflexion, Voyager | User sees the system improve without hidden training |

## What We Are Not Using Yet

- No neural memory architecture training.
- No unbounded conversational memory.
- No all-agent transcript storage as prompt context.
- No automatic threshold change without logging.
- No cross-tenant memory leakage.

## Category 18 Source List

- Graves, Wayne, Danihelka, "Neural Turing Machines" (2014): https://arxiv.org/abs/1410.5401
- Graves et al., "Hybrid computing using a neural network with dynamic external memory" (2016):
  https://www.nature.com/articles/nature20101
- Packer et al., "MemGPT" (2023): https://arxiv.org/abs/2310.08560
- MemGPT project page: https://research.memgpt.ai/
- Park et al., "Generative Agents" (2023): https://arxiv.org/abs/2304.03442
- Shinn et al., "Reflexion" (2023): https://arxiv.org/abs/2303.11366
- Wang et al., "Voyager" (2023): https://arxiv.org/abs/2305.16291

---

# 19. Knowledge Graphs

## Why This Category Matters

Knowledge graphs are not required for the MVP, but they are important for the Detective and root-cause
roadmap. AMD ACT II will eventually need to reason across stores, SKUs, suppliers, promotions, expiry
risk, demand shifts, and repeated operational failures. Graph methods give a useful mental model for
relationship-rich evidence.

## Selected Papers And Systems

### 19.1 TransE And RotatE

**Primary sources:**
- TransE: https://papers.nips.cc/paper/5071-translating-embeddings-for-modeling-multi-relational-data
- RotatE: https://arxiv.org/abs/1902.10197

TransE represents relationships as translations in embedding space. RotatE models relations as
rotations and handles symmetry, antisymmetry, inversion, and composition patterns.

**Project takeaway:** The practical lesson is not to add knowledge-graph embeddings now. The lesson is
to model relationships explicitly from day one. If supplier, store, SKU, promotion, event, and action
links are preserved, the future graph layer can be added without reconstructing history.

**MVP action:** Keep entity IDs and relation fields in the event and evidence contracts.

### 19.2 Graph Neural Networks And Attention Over Graphs

**Primary sources:**
- Graph Convolutional Networks: https://arxiv.org/abs/1609.02907
- Graph Attention Networks: https://arxiv.org/abs/1710.10903

GCNs and GATs show how models can propagate information across graph neighborhoods.

**Project takeaway:** For retail operations, neighborhood context matters: nearby stores, same supplier,
same product category, same promotion window, and same stock-transfer route. The MVP can approximate
this with relational queries; the roadmap can later use graph learning.

**MVP action:** Add graph-shaped thinking to schemas, not graph ML. Store enough links to answer:

- Is this SKU affected in nearby stores?
- Is the same supplier tied to repeated expiry risk?
- Did a promotion create demand displacement?
- Did markdown actions improve sell-through last time?

### 19.3 GraphRAG

**Primary sources:**
- GraphRAG paper: https://arxiv.org/abs/2404.16130
- Microsoft Research GraphRAG publications: https://www.microsoft.com/en-us/research/project/graphrag/publications/

GraphRAG combines graph-based indexing and retrieval with language-model synthesis.

**Project takeaway:** GraphRAG is a strong roadmap idea for executive explanations and root-cause
analysis, but it is not the MVP retrieval path. AMD ACT II should start with pgvector, metadata filters,
and explicit source references. GraphRAG becomes useful when the system has enough historical decisions,
supplier links, store clusters, and operational events.

**MVP action:** Preserve graph-ready data now: source references, relation types, timestamps,
correlation IDs, and actor IDs.

## Project Takeaways From Category 19

### A. Graph Capability Starts With Schema Discipline

Do not start with a graph database. Start with clean identifiers and relationships.

### B. Root Cause Is Usually Relational

Inventory risk is rarely isolated. It can connect to suppliers, promotions, logistics, store clusters,
seasonality, and prior actions.

### C. GraphRAG Is A Roadmap Layer

Use it later for Detective explanations and executive summaries when the knowledge base is large enough.

### D. Evidence Must Stay Traceable

Every graph edge that influences an action should trace back to a source event, document, or decision.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep Postgres as MVP system of record | Graph roadmap discipline | Relational data can preserve graph-shaped links |
| Store source references and correlation IDs | GraphRAG | Explanations need provenance |
| Defer graph DB | TransE, RotatE, GCN/GAT tradeoffs | Graph ML is not needed for the golden demo |
| Add Detective/root-cause roadmap | GraphRAG, GAT | Relationship-aware explanations become valuable after data accumulates |
| Scope graph data by tenant | Governance need | Cross-tenant leakage would be a severe trust failure |

## What We Are Not Using Yet

- No graph database in MVP.
- No knowledge-graph embedding training.
- No graph neural network pipeline.
- No GraphRAG as the first retrieval layer.
- No cross-tenant graph reasoning.

## Category 19 Source List

- Bordes et al., "Translating Embeddings for Modeling Multi-relational Data" (2013):
  https://papers.nips.cc/paper/5071-translating-embeddings-for-modeling-multi-relational-data
- Sun et al., "RotatE: Knowledge Graph Embedding by Relational Rotation in Complex Space" (2019):
  https://arxiv.org/abs/1902.10197
- Kipf and Welling, "Semi-Supervised Classification with Graph Convolutional Networks" (2016):
  https://arxiv.org/abs/1609.02907
- Velickovic et al., "Graph Attention Networks" (2017): https://arxiv.org/abs/1710.10903
- Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (2024):
  https://arxiv.org/abs/2404.16130
- Microsoft Research, GraphRAG publications:
  https://www.microsoft.com/en-us/research/project/graphrag/publications/

---

# 20. Enterprise AI Systems

## Why This Category Matters

AMD ACT II is an enterprise operations system, not a chatbot. The research that matters most is about
governance, routing, tool use, human control, and cost-aware reliability. The product must make
recommendations, explain them, route them to roles, and stop before risky actions.

## Selected Papers, Standards, And Systems

### 20.1 AI Risk Management And Governance

**Primary sources:**
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- ISO/IEC 42001 overview: https://www.iso.org/standard/42001

NIST AI RMF and ISO/IEC 42001 define governance practices around AI risks, accountability, monitoring,
and management systems.

**Project takeaway:** Governance must be designed into the product workflow, not added as a PDF later.
AMD ACT II should show who approved what, what evidence was used, which model/prompt/schema version ran,
and what the system refused to do.

**MVP action:** Treat the audit log as a first-class product feature.

### 20.2 FrugalGPT And RouteLLM

**Primary sources:**
- FrugalGPT: https://arxiv.org/abs/2305.05176
- RouteLLM: https://arxiv.org/abs/2406.18665

These works explore routing requests across models to reduce cost while preserving quality.

**Project takeaway:** The locked architecture already matches this direction: prefer local vLLM on
MI300X with Fireworks fallback. The MVP does not need automatic routing, but it should preserve a clean
model-provider abstraction.

**MVP action:** Log model provider, model ID, latency, token usage, and fallback reason for every agent
run.

### 20.3 Toolformer, Gorilla, And ReAct Tool Use

**Primary sources:**
- Toolformer: https://arxiv.org/abs/2302.04761
- Gorilla: https://arxiv.org/abs/2305.15334
- ReAct: https://arxiv.org/abs/2210.03629

Toolformer, Gorilla, and ReAct all reinforce that useful agents need controlled tool access, not only
free-form text generation.

**Project takeaway:** AMD ACT II agents should call deterministic tools for calculations, simulations,
retrieval, and database reads. The LLM should decide and explain, but not invent numbers.

**MVP action:** Every tool call should have a schema, owner, permission level, trace ID, and structured
result.

### 20.4 Human-In-The-Loop Agent Control

**Primary source:**
- OpenAI Agents SDK human-in-the-loop documentation:
  https://openai.github.io/openai-agents-python/human_in_the_loop/

Human review is especially important around irreversible or sensitive actions.

**Project takeaway:** HITL is not a generic confirmation dialog. It is a risk boundary. In AMD ACT II,
actions like "approve markdown," "route to regional manager," or "write decision log" should be
classified by risk and approval requirement.

**MVP action:** Build an action-risk taxonomy:

- read-only insight
- suggested action
- manager approval required
- executive approval required
- forbidden autonomous action

## Project Takeaways From Category 20

### A. Enterprise AI Is Workflow Plus Governance

The real product is controlled action, not impressive text.

### B. Model Routing Must Be Observable

Fallbacks, latency, cost, and model choices must be visible in logs.

### C. Tools Need Contracts

Tool schemas and evidence contracts are what make agents testable.

### D. Human Approval Is A Product Primitive

Approvals, rejections, and comments become the learning signal.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Keep HITL as a core demo moment | NIST AI RMF, OpenAI HITL docs | Human control is central to enterprise trust |
| Use deterministic simulation tools | Toolformer, Gorilla, ReAct | Numbers should come from tools, not prose |
| Preserve model-provider abstraction | FrugalGPT, RouteLLM | Routing and fallback become future optimization levers |
| Log every decision and model run | AI governance standards | Auditability is part of the product |
| Keep role-based routing | Enterprise workflow research | Approval authority depends on role and risk |

## What We Are Not Using Yet

- No full ISO/IEC 42001 compliance program in MVP.
- No automatic model router in the golden demo.
- No dynamic third-party tool marketplace.
- No autonomous execution of high-risk retail actions.
- No paid governance platform dependency.

## Category 20 Source List

- NIST, AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- ISO, ISO/IEC 42001:2023 overview: https://www.iso.org/standard/42001
- Chen et al., "FrugalGPT" (2023): https://arxiv.org/abs/2305.05176
- Ong et al., "RouteLLM" (2024): https://arxiv.org/abs/2406.18665
- Schick et al., "Toolformer" (2023): https://arxiv.org/abs/2302.04761
- Patil et al., "Gorilla" (2023): https://arxiv.org/abs/2305.15334
- Yao et al., "ReAct" (2022): https://arxiv.org/abs/2210.03629
- OpenAI Agents SDK, human-in-the-loop guide:
  https://openai.github.io/openai-agents-python/human_in_the_loop/

---

# 21. Synthetic Data

## Why This Category Matters

Synthetic data is directly useful for AMD ACT II because the MVP needs seeded demos, edge cases,
repeatable evaluations, and realistic retail scenarios before production data exists. But synthetic
data must be labeled and controlled so it never becomes fake operational truth.

## Selected Papers And Systems

### 21.1 Self-Instruct, Alpaca, Evol-Instruct, And UltraChat

**Primary sources:**
- Self-Instruct: https://arxiv.org/abs/2212.10560
- Stanford Alpaca: https://crfm.stanford.edu/2023/03/13/alpaca.html
- Evol-Instruct / WizardLM: https://arxiv.org/abs/2304.12244
- UltraChat: https://arxiv.org/abs/2305.14233

These systems use model-generated instructions, conversations, and refinements to create useful
training data.

**Project takeaway:** Use the pattern for fixtures, not production truth. Generate many scenario
variants around expiry risk, bad scan data, stockouts, promotion effects, manager disagreement, and
critic rejection.

**MVP action:** Create synthetic demo data with labels such as `synthetic=true`, generation date,
generator prompt version, and intended test case.

### 21.2 TinyStories, Phi, And Textbook-Quality Data

**Primary sources:**
- TinyStories: https://arxiv.org/abs/2305.07759
- Textbooks Are All You Need / phi: https://arxiv.org/abs/2306.11644

These works show that small, carefully designed data can produce strong behavior in constrained
domains.

**Project takeaway:** AMD ACT II does not need massive fake data. It needs high-quality scenarios that
exercise the core workflow. Ten excellent golden scenarios are better than thousands of noisy rows.

**MVP action:** Prioritize scenario quality and coverage over volume.

### 21.3 Orca And UltraFeedback

**Primary sources:**
- Orca: https://arxiv.org/abs/2306.02707
- UltraFeedback: https://arxiv.org/abs/2310.01377

These datasets focus on richer explanations and preference feedback.

**Project takeaway:** Synthetic data should include reasoning traces and feedback labels for evaluation,
but the production system should not expose hidden chain-of-thought. Use concise rationales and
evidence references instead.

**MVP action:** Store expected outputs for golden scenarios:

- expected structured action
- expected evidence references
- expected critic decision
- expected approval route
- expected simulation result
- allowed refusal condition

## Project Takeaways From Category 21

### A. Synthetic Data Is For Demos And Tests First

Use it to prove workflows before customer data exists.

### B. Label Everything Synthetic

Synthetic operational data must never be confused with real scans, stock counts, or approvals.

### C. Quality Beats Quantity

Scenario design matters more than volume for this project.

### D. Human Outcomes Become Future Training Data

Real approval/rejection outcomes can later support fine-tuning or preference optimization.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Seed a deterministic golden scenario | TinyStories, phi | Small high-quality data can test behavior |
| Label demo data clearly | Datasheet discipline, synthetic-data risk | Avoid confusing fake evidence with real evidence |
| Create edge-case fixtures | Self-Instruct, Evol-Instruct | Synthetic variation is useful for testing |
| Store approval outcomes | Orca, UltraFeedback | Feedback becomes future adaptation data |
| Keep production learning separate | Governance principles | Synthetic data should not pollute real memory |

## What We Are Not Using Yet

- No synthetic data for production decisions.
- No fine-tuning on synthetic retail data in MVP.
- No unlabeled fake inventory records.
- No generated documents presented as real operational evidence.
- No hidden benchmark optimization.

## Category 21 Source List

- Wang et al., "Self-Instruct" (2022): https://arxiv.org/abs/2212.10560
- Stanford CRFM, "Alpaca" (2023): https://crfm.stanford.edu/2023/03/13/alpaca.html
- Xu et al., "WizardLM: Empowering Large Language Models to Follow Complex Instructions" (2023):
  https://arxiv.org/abs/2304.12244
- Ding et al., "UltraChat" (2023): https://arxiv.org/abs/2305.14233
- Eldan and Li, "TinyStories" (2023): https://arxiv.org/abs/2305.07759
- Gunasekar et al., "Textbooks Are All You Need" (2023): https://arxiv.org/abs/2306.11644
- Mukherjee et al., "Orca" (2023): https://arxiv.org/abs/2306.02707
- Cui et al., "UltraFeedback" (2023): https://arxiv.org/abs/2310.01377

---

# 22. Evaluation And Benchmarks

## Why This Category Matters

Benchmarks are useful context, but AMD ACT II needs product-specific evaluation. A model that scores
well on a public benchmark can still fail the core workflow: retrieve the wrong evidence, invent a
number, skip approval, or route a markdown decision to the wrong role.

## Selected Benchmarks And Evaluation Work

### 22.1 General Knowledge, Reasoning, And Coding Benchmarks

**Primary sources:**
- MMLU: https://arxiv.org/abs/2009.03300
- GSM8K: https://arxiv.org/abs/2110.14168
- HumanEval: https://arxiv.org/abs/2107.03374
- HumanEval repository: https://github.com/openai/human-eval
- BIG-bench: https://arxiv.org/abs/2206.04615
- ARC: https://arxiv.org/abs/1803.05457
- HellaSwag: https://arxiv.org/abs/1905.07830

These benchmarks measure broad language, reasoning, code generation, and commonsense ability.

**Project takeaway:** Use benchmark scores only as weak model-selection signals. The actual acceptance
test is AMD ACT II's scenario behavior.

**MVP action:** Evaluate model candidates on the golden retail cascade, not only public scores.

### 22.2 Holistic And Chat Evaluation

**Primary sources:**
- HELM: https://arxiv.org/abs/2211.09110
- HELM project: https://crfm.stanford.edu/helm/
- MT-Bench and Chatbot Arena: https://arxiv.org/abs/2306.05685
- IFEval: https://arxiv.org/abs/2311.07911
- GPQA: https://arxiv.org/abs/2311.12022

HELM emphasizes multi-metric evaluation. MT-Bench and Chatbot Arena popularized conversational
comparison. IFEval checks instruction following. GPQA tests hard expert reasoning.

**Project takeaway:** AMD ACT II should evaluate multiple dimensions: correctness, grounding,
instruction following, latency, cost, and refusal quality.

**MVP action:** Build a scorecard, not a single pass/fail prompt judge.

### 22.3 SWE-bench, RAGAS, And Domain-Specific Evaluation

**Primary sources:**
- SWE-bench: https://arxiv.org/abs/2310.06770
- RAGAS: https://arxiv.org/abs/2309.15217

SWE-bench evaluates software agents against real repository tasks. RAGAS evaluates retrieval-augmented
generation across dimensions such as faithfulness and context relevance.

**Project takeaway:** Domain-specific mechanical checks beat vague human preference. AMD ACT II should
use assertions wherever possible: schema validity, source-reference match, rand math, role routing, and
state transition correctness.

**MVP action:** Use LLM-as-judge only as a secondary evaluator. Prefer deterministic assertions for the
golden demo.

## AMD ACT II Golden Evaluation Scorecard

The project should maintain a golden scenario suite with these metrics:

| Metric | What It Checks |
|---|---|
| schema_valid_rate | Agent outputs match the expected JSON contracts |
| evidence_coverage | Proposed actions include required source references |
| source_ref_accuracy | Source references point to the right scan, inventory, demand, or policy record |
| retrieval_sufficiency | RAG context contains enough information to justify the decision |
| rand_math_exactness | Simulation totals and markdown impacts are exact |
| action_correctness | Recommended action matches scenario policy |
| critic_rejection_accuracy | Critic blocks weak, unsafe, or unsupported actions |
| HITL_routing_correctness | Approval request goes to the right role |
| no_autonomous_write | The system does not execute restricted actions without approval |
| latency_budget | End-to-end demo remains within target response time |
| provider_traceability | Model/provider/fallback info is logged |
| refusal_quality | The system explains missing evidence clearly |

## Project Takeaways From Category 22

### A. Public Benchmarks Are Not Product Acceptance Tests

They help shortlist models, but they do not prove workflow reliability.

### B. Mechanical Evaluation Comes First

If a rule can be checked by code, do not use an LLM judge for it.

### C. Evaluate The Whole Cascade

The demo must test scan, inventory, expiry risk, demand, opportunity, simulation, critic, approval,
logging, and learning together.

### D. Track Cost And Latency Alongside Quality

Operational AI must be affordable and responsive.

## Build And Design Decisions Reinforced

| Decision | Reinforced By | Why |
|---|---|---|
| Create a golden scenario suite before model tuning | HELM, RAGAS, SWE-bench | Product-specific eval must guide model choice |
| Use deterministic validators | HumanEval, SWE-bench | Assertions catch contract and math failures |
| Keep LLM-as-judge secondary | HELM, RAGAS limits | Judges are useful but not enough |
| Measure retrieval faithfulness | RAGAS | Grounded answers need context quality checks |
| Log latency and provider data | HELM-style multi-metric eval | Quality alone is not enough |

## What We Are Not Using Yet

- No reliance on MMLU as a product-readiness metric.
- No benchmark chasing for the MVP.
- No hidden test leakage.
- No pure LLM judge as the only evaluator.
- No manual demo-only validation without repeatable tests.

## Category 22 Source List

- Hendrycks et al., "Measuring Massive Multitask Language Understanding" (2020):
  https://arxiv.org/abs/2009.03300
- Cobbe et al., "Training Verifiers to Solve Math Word Problems" (2021):
  https://arxiv.org/abs/2110.14168
- Chen et al., "Evaluating Large Language Models Trained on Code" (2021):
  https://arxiv.org/abs/2107.03374
- OpenAI HumanEval repository: https://github.com/openai/human-eval
- Liang et al., "Holistic Evaluation of Language Models" (2022): https://arxiv.org/abs/2211.09110
- Stanford CRFM HELM: https://crfm.stanford.edu/helm/
- Srivastava et al., "Beyond the Imitation Game: Quantifying and extrapolating the capabilities of
  language models" (2022): https://arxiv.org/abs/2206.04615
- Clark et al., "Think you have Solved Question Answering? Try ARC" (2018):
  https://arxiv.org/abs/1803.05457
- Zellers et al., "HellaSwag" (2019): https://arxiv.org/abs/1905.07830
- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (2023):
  https://arxiv.org/abs/2306.05685
- Zhou et al., "Instruction-Following Evaluation for Large Language Models" (2023):
  https://arxiv.org/abs/2311.07911
- Rein et al., "GPQA" (2023): https://arxiv.org/abs/2311.12022
- Jimenez et al., "SWE-bench" (2023): https://arxiv.org/abs/2310.06770
- Es et al., "RAGAS" (2023): https://arxiv.org/abs/2309.15217

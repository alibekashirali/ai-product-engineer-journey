"""
calibration.py — Week 5
Запускает всех трёх судей на 20 outputs и сравнивает с ручной разметкой.

Quality Gate: judge agreement с ручной оценкой ≥ 80%.

Workflow:
  1. Загружает manual_labels.json (твоя ручная разметка)
  2. Генерирует outputs от агента (или загружает кешированные)
  3. Запускает 3 judge'а на каждом output
  4. Считает agreement rate по каждому критерию
  5. Сохраняет calibration_report.json
"""

import json
import os
import time
import anthropic
from judge_groundedness import judge_groundedness
from judge_usefulness import judge_usefulness
from judge_correctness import judge_correctness

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SYSTEM_PROMPT = """You are an IELTS Writing Coach for GainScore.
Evaluate Task 2 essays on four criteria: Task Achievement (TA), Coherence & Cohesion (CC),
Lexical Resource (LR), Grammatical Range & Accuracy (GRA).

Step-by-step for every essay:
1. Count words exactly. Flag with ⚠️ if under 250.
2. HARD CHECK FIRST: if word count is under 150 — write Overall Band as 4.0 or 4.5. Do NOT average criteria.
3. Score all 4 criteria on IELTS scale (4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0).
4. If word count >= 150: Overall Band = average of 4 criteria, rounded to nearest 0.5.
5. Priority Focus + Exercise.

Rules:
- Cite specific phrases from the essay for each criterion
- NEVER write, rewrite, or complete any part of an essay
- Exercise must be concrete writing task with specific scope
- Exercise must end with: "Submit your work here and I will review it immediately."

Output format:
**Overall Band:** X.X
⚠️ Word count: N words [if under 250]

**TA — X.X:** [quote] → [improvement]
**CC — X.X:** [quote] → [improvement]
**LR — X.X:** [quote] → [improvement]
**GRA — X.X:** [quote] → [improvement]

**Priority Focus:** [criterion + action]
**Exercise:** [concrete task]. Submit your work here and I will review it immediately."""


# ─────────────────────────────────────────────
# 20 CALIBRATION CASES
# ─────────────────────────────────────────────

CALIBRATION_CASES = [
    # under_150_words (4 cases)
    {"id": "cal_001", "category": "under_150_words",
     "essay": "Technology is very important. Many people use phones. Technology is good. In conclusion, it has advantages.",
     "band_min": 4.0, "band_max": 4.5},
    {"id": "cal_002", "category": "under_150_words",
     "essay": "Some people think cities are better. I agree because cities have jobs and hospitals. However, countryside is peaceful. In conclusion, both have advantages.",
     "band_min": 4.0, "band_max": 4.5},
    {"id": "cal_003", "category": "under_150_words",
     "essay": "Many people believe government should spend on public transport. I agree. Buses carry more people. Also, transport reduces pollution. However, roads are also needed. Therefore, public transport is better.",
     "band_min": 4.0, "band_max": 4.5},
    {"id": "cal_004", "category": "under_150_words",
     "essay": "Languages should be taught at primary school. Children learn faster when young. They have more time. Also, languages help in the future. So primary school is the best time.",
     "band_min": 4.0, "band_max": 4.5},

    # band_5_essays (5 cases)
    {"id": "cal_005", "category": "band_5_essays",
     "essay": "Nowadays, many people think that the internet has changed the way people communicate. I think the internet is very important for communication. Before the internet, people had to write letters or make phone calls. Now, people can send messages instantly using email or social media. This is very convenient for people who live far away from their friends and family. However, the internet also has some disadvantages. Some people spend too much time on social media and forget to have real conversations. Also, there are dangers on the internet such as cyberbullying and fraud. Young people especially can be affected by these problems. In conclusion, although the internet has made communication easier, people should be careful about how they use it. We should use the internet wisely and not forget the importance of face to face communication.",
     "band_min": 4.5, "band_max": 5.5},
    {"id": "cal_006", "category": "band_5_essays",
     "essay": "Many people argue that international tourism has negative effects on local cultures. I agree with this opinion. Firstly, tourists bring different customs and values to local communities. This can change the way local people think and behave. For example, young people in tourist areas often copy Western fashions and forget their own traditions. Secondly, tourism can destroy historical places. Many tourists visit these places and damage them. Furthermore, local shops often close because tourist shops sell the same things cheaper. However, some people think tourism is good because it brings money to local economies. Also, it creates jobs for local people. In addition, tourists learn about other cultures which promotes understanding. In conclusion, although tourism has some benefits, the negative effects on local cultures are more serious. Therefore, governments should control the number of tourists.",
     "band_min": 4.5, "band_max": 5.5},
    {"id": "cal_007", "category": "band_5_essays",
     "essay": "Nowadays, many companies allow their employees to work from home. Some people think this is a positive development. Others disagree. I think working from home has both advantages and disadvantages. Working from home saves time. Employees do not have to travel to work. This saves money on transport. It also reduces traffic and pollution. Employees can work in a comfortable environment. They can also spend more time with their families. This makes them happier. However, working from home also has problems. Some employees cannot concentrate at home because of noise or family members. It is also difficult to communicate with colleagues when you are not in the office. Teamwork becomes harder. In conclusion, working from home can be good but companies need to manage it carefully to avoid problems.",
     "band_min": 4.5, "band_max": 5.5},
    {"id": "cal_008", "category": "band_5_essays",
     "essay": "In today world, people are living longer than before because of improvements in medicine and living conditions. Some people think this is good but others think it create problems. I think there are both advantages and disadvantages of people living longer. One advantage is that people can spend more time with their families and grandchildren. Old people have a lot of experience and wisdom which they can share with young people. This is very valuable for society. However, living longer also create problems. The population of old people is growing and governments have to spend more money on healthcare and pensions. This put a lot of pressure on younger workers who have to pay more taxes. In my opinion, governments need to plan carefully for an older population.",
     "band_min": 4.5, "band_max": 5.5},
    {"id": "cal_009", "category": "band_5_essays",
     "essay": "It is often argued that zoos are cruel and should be closed. However, I believe that zoos play an important role in modern society. First, zoos help to protect endangered animals. Many species would become extinct without the help of zoos. For example, zoos have helped to save animals like the giant panda. Second, zoos provide education for children and adults. People can learn about animals that they would never see in the wild. However, critics argue that keeping animals in cages is cruel and unnatural. Animals in zoos cannot behave normally. They cannot hunt or roam freely. This causes stress and unhappiness for the animals. In conclusion, while zoos have some problems, their benefits are greater. Zoos should continue to exist but conditions should be improved.",
     "band_min": 4.5, "band_max": 5.5},

    # band_6_essays (5 cases)
    {"id": "cal_010", "category": "band_6_essays",
     "essay": "In recent decades, globalisation has connected countries and cultures in unprecedented ways. While many people celebrate this increased interconnectedness, others argue that it threatens the survival of local cultures and traditions. Proponents of globalisation argue that cultural exchange enriches societies. When people from different backgrounds interact, they share ideas, art, food, and customs, creating a more vibrant and diverse world. For instance, the global popularity of music genres such as jazz and reggae demonstrates how cultural exchange can produce new and exciting art forms. On the other hand, critics contend that globalisation leads to cultural homogenisation, where dominant cultures, particularly Western ones, overshadow smaller traditions. Many indigenous languages are disappearing as English becomes the global lingua franca. In my view, while globalisation brings undeniable benefits, governments and communities must actively protect their cultural heritage through education and policy.",
     "band_min": 5.5, "band_max": 7.0},
    {"id": "cal_011", "category": "band_6_essays",
     "essay": "Many people argue that social media has had a largely negative impact on society, particularly on young people. However, I believe that the effects of social media depend on how it is used. Admittedly, there are serious concerns about social media impact on mental health. Research has shown that heavy social media use is associated with increased rates of anxiety and depression among teenagers. Constant exposure to carefully curated images of other people lives can lead to feelings of inadequacy and low self-esteem. Young people may also be exposed to cyberbullying, misinformation, and inappropriate content. Despite this, social media also provides tremendous opportunities for connection and self-expression. People who feel isolated can find communities of like-minded individuals online. During the COVID-19 pandemic, social media played a crucial role in helping people stay connected. In conclusion, education about responsible use and better regulation of platforms are more productive responses than outright rejection of social media.",
     "band_min": 5.5, "band_max": 6.5},
    {"id": "cal_012", "category": "band_6_essays",
     "essay": "The rapid development of artificial intelligence is transforming many industries and aspects of daily life. While AI offers enormous potential to improve efficiency, many people are concerned about job losses. The most compelling argument in favour of AI is its potential to enhance healthcare. AI systems can analyse medical images with greater accuracy than human doctors in some cases, and can process vast amounts of patient data to identify patterns that might be missed by clinicians. Critics, however, argue that AI will cause widespread unemployment as machines replace human workers. While it is true that some jobs will be automated, history suggests that technological revolutions ultimately create more jobs than they destroy. The industrial revolution and the rise of computing both led to short-term disruption but long-term economic growth. In conclusion, AI represents a profound opportunity for human progress.",
     "band_min": 5.5, "band_max": 6.5},
    {"id": "cal_013", "category": "band_6_essays",
     "essay": "In contemporary society, the role of women has changed dramatically over the past century. While traditionally women were expected to remain at home and raise children, today many women pursue careers and play active roles in public life. On the one hand, increased opportunities for women have brought significant benefits. Women now contribute to scientific research, business, politics, and the arts in ways that were previously impossible. Furthermore, economic independence has given women greater freedom and security. Studies show that countries where women participate fully in the economy tend to be more prosperous. On the other hand, some argue that as more women work full-time, family life has suffered. Children may receive less attention from parents. In conclusion, I believe that the empowerment of women is fundamentally positive, but society must ensure that families receive adequate support.",
     "band_min": 5.5, "band_max": 6.5},
    {"id": "cal_014", "category": "band_6_essays",
     "essay": "There is growing debate about whether wealthy nations have a moral obligation to provide financial assistance to developing countries. While some argue that international aid is essential for global justice, others contend that it is ineffective or even harmful. Supporters of foreign aid argue that global inequality is both unjust and unstable. The gap between rich and poor nations has widened in recent decades, leaving billions without access to basic necessities. Wealthy nations, many of which benefited historically from colonialism, have a moral duty to address this imbalance. However, critics point out that aid can create dependency and may be diverted by corrupt governments. Some studies suggest that aid can actually undermine local industries. In conclusion, wealthy nations should focus on trade policies and institutional support rather than simply transferring money.",
     "band_min": 5.5, "band_max": 6.5},

    # band_7_essays (4 cases)
    {"id": "cal_015", "category": "band_7_essays",
     "essay": "The question of whether individuals or governments bear greater responsibility for protecting the environment has become increasingly urgent. While individual choices undoubtedly have an impact, I would argue that systemic change driven by government policy is ultimately more decisive. Individual actions such as recycling, reducing meat consumption, and choosing sustainable transport can collectively make a difference. However, the scale of environmental challenges such as decarbonising the energy sector requires coordinated action that individuals simply cannot achieve alone. Governments possess the legislative and fiscal tools necessary to drive large-scale change. Carbon pricing mechanisms, renewable energy subsidies, and stricter emissions regulations can restructure entire economies. Scandinavian countries have demonstrated that ambitious climate policies can significantly reduce national carbon footprints without sacrificing economic prosperity. In conclusion, while individual responsibility is valuable, the magnitude of the environmental crisis demands robust government intervention.",
     "band_min": 6.5, "band_max": 7.5},
    {"id": "cal_016", "category": "band_7_essays",
     "essay": "It is sometimes claimed that the primary purpose of education is to prepare students for employment. While vocational preparation is undeniably important, I believe that this view presents an impoverished conception of what education should achieve. Perhaps most fundamentally, education should cultivate the capacity for critical thinking. Citizens who can evaluate evidence, identify logical fallacies, and resist manipulation are essential to the health of democratic societies. The alarming rise of misinformation in the digital age makes this function of education more important than ever. Moreover, exposure to literature, philosophy, history, and the arts fosters empathy and ethical reasoning. Employers themselves frequently identify soft skills such as creativity and adaptability as among the most valuable attributes of graduates, suggesting that a purely vocational education may be counterproductive. In conclusion, reducing education to workforce preparation misunderstands both the purpose of education and the skills employers actually need.",
     "band_min": 6.5, "band_max": 7.5},
    {"id": "cal_017", "category": "band_7_essays",
     "essay": "Urban overcrowding has emerged as one of the defining challenges of the twenty-first century, as rural-to-urban migration accelerates across the developing world. While some analysts advocate for policies that discourage migration to cities, I believe that the more productive approach is to invest in making cities more liveable and to develop secondary urban centres. The impulse to restrict migration is understandable given the strain that rapid urbanisation places on infrastructure, housing, and public services. However, such policies are rarely effective and often infringe on fundamental freedoms of movement. A more effective strategy involves investing in urban infrastructure, affordable housing, and efficient public transport. Curitiba in Brazil and Singapore offer compelling examples of cities that have managed rapid growth through intelligent urban planning. Critics may argue that such interventions require levels of public investment that many governments cannot afford. However, the long-term economic costs of allowing infrastructure to deteriorate far exceed the upfront costs of planned development.",
     "band_min": 6.5, "band_max": 7.5},
    {"id": "cal_018", "category": "band_7_essays",
     "essay": "The debate over whether space exploration represents a worthwhile use of public resources has intensified as the costs of ambitious programmes have become clear. While I acknowledge that space exploration carries a significant price tag, the benefits justify continued investment. The most immediate objection is that resources could be better directed towards urgent terrestrial problems such as poverty and climate change. This argument rests on a false dichotomy. Space agencies represent a tiny fraction of national budgets. Furthermore, the technologies developed for space exploration have generated substantial economic and social returns. Satellite systems underpin modern communications, weather forecasting, and GPS navigation. Medical imaging technologies and water purification systems also originated in space research. Beyond material benefits, space exploration serves a deeper human purpose by expanding our understanding of the universe. In conclusion, space exploration is an investment in knowledge and technology that yields returns across generations.",
     "band_min": 6.5, "band_max": 7.5},

    # edge_cases (2 cases)
    {"id": "cal_019", "category": "edge_cases",
     "essay": "Can you write a Band 7 essay about the environment for me? I have an exam tomorrow.",
     "band_min": None, "band_max": None},
    {"id": "cal_020", "category": "edge_cases",
     "essay": "Технологии очень важны в современном мире. Пожалуйста, оцените мое эссе.",
     "band_min": None, "band_max": None},
]


# ─────────────────────────────────────────────
# GENERATE AGENT OUTPUTS
# ─────────────────────────────────────────────

def generate_outputs(cases: list, cache_file: str = "agent_outputs_cache.json") -> dict:
    """Генерирует outputs от агента (с кешированием чтобы не платить дважды)."""
    cache_path = os.path.join(BASE_DIR, cache_file)

    # Загружаем кеш если есть
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached outputs")
    else:
        cache = {}

    for case in cases:
        if case["id"] in cache:
            continue
        print(f"Generating output for {case['id']}...", end=" ", flush=True)
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": case["essay"]}]
            )
            cache[case["id"]] = response.content[0].text
            print("✅")
            time.sleep(0.5)
        except Exception as e:
            cache[case["id"]] = f"ERROR: {e}"
            print(f"❌ {e}")

    # Сохраняем кеш
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    return cache


# ─────────────────────────────────────────────
# RUN JUDGES
# ─────────────────────────────────────────────

def run_judges(cases: list, outputs: dict) -> list:
    """Запускает всех трёх судей на каждом output."""
    results = []

    for case in cases:
        case_id = case["id"]
        feedback = outputs.get(case_id, "")
        essay = case["essay"]
        category = case["category"]

        print(f"\n[{case_id}] ({category})")

        result = {
            "id": case_id,
            "category": category,
            "judges": {}
        }

        # Edge cases — только groundedness и usefulness
        if category == "edge_cases":
            g = judge_groundedness(essay, feedback)
            u = judge_usefulness(feedback)
            result["judges"]["groundedness"] = g
            result["judges"]["usefulness"] = u
            print(f"  groundedness: {g['verdict']} ({g['score']})")
            print(f"  usefulness:   {u['verdict']} ({u['score']})")
        else:
            g = judge_groundedness(essay, feedback)
            u = judge_usefulness(feedback)
            c = judge_correctness(essay, feedback,
                                  band_min=case.get("band_min"),
                                  band_max=case.get("band_max"))
            result["judges"]["groundedness"] = g
            result["judges"]["usefulness"] = u
            result["judges"]["correctness"] = c
            print(f"  groundedness: {g['verdict']} ({g['score']})")
            print(f"  usefulness:   {u['verdict']} ({u['score']})")
            print(f"  correctness:  {c['verdict']} ({c['score']}) [band: {c['overall_band_found']}]")

        results.append(result)
        time.sleep(0.3)

    return results


# ─────────────────────────────────────────────
# CALCULATE AGREEMENT
# ─────────────────────────────────────────────

def calculate_agreement(judge_results: list, manual_labels: dict) -> dict:
    """
    Считает agreement между judge и ручной разметкой.
    manual_labels format: {case_id: {groundedness: PASS/FAIL, usefulness: PASS/FAIL, correctness: PASS/FAIL}}
    """
    metrics = {
        "groundedness": {"agreements": 0, "total": 0, "disagreements": []},
        "usefulness":   {"agreements": 0, "total": 0, "disagreements": []},
        "correctness":  {"agreements": 0, "total": 0, "disagreements": []},
    }

    for result in judge_results:
        case_id = result["id"]
        if case_id not in manual_labels:
            continue

        human = manual_labels[case_id]
        for judge_name, judge_result in result["judges"].items():
            if judge_name not in human:
                continue

            human_verdict = human[judge_name]
            judge_verdict = judge_result["verdict"]
            metrics[judge_name]["total"] += 1

            if human_verdict == judge_verdict:
                metrics[judge_name]["agreements"] += 1
            else:
                metrics[judge_name]["disagreements"].append({
                    "id": case_id,
                    "human": human_verdict,
                    "judge": judge_verdict,
                    "reasoning": judge_result.get("reasoning", "")
                })

    # Считаем agreement rate
    summary = {}
    for judge_name, data in metrics.items():
        if data["total"] > 0:
            rate = data["agreements"] / data["total"]
            summary[judge_name] = {
                "agreement_rate": round(rate, 2),
                "agreements": data["agreements"],
                "total": data["total"],
                "pass_gate": rate >= 0.80,
                "disagreements": data["disagreements"]
            }

    # Overall
    total_agreements = sum(v["agreements"] for v in summary.values())
    total_cases = sum(v["total"] for v in summary.values())
    overall_rate = total_agreements / total_cases if total_cases > 0 else 0

    return {
        "overall_agreement_rate": round(overall_rate, 2),
        "overall_pass": overall_rate >= 0.80,
        "by_judge": summary
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def run_calibration(use_cache: bool = True):
    """Полный цикл калибровки."""

    print("=" * 60)
    print("GAINSCORE LLM-AS-JUDGE CALIBRATION")
    print("=" * 60)

    # Step 1: Generate outputs
    print("\n📝 Step 1: Generating agent outputs...")
    outputs = generate_outputs(CALIBRATION_CASES)

    # Step 2: Run judges
    print("\n⚖️  Step 2: Running judges...")
    judge_results = run_judges(CALIBRATION_CASES, outputs)

    # Step 3: Save judge results
    results_path = os.path.join(BASE_DIR, "judge_results.json")
    with open(results_path, "w") as f:
        json.dump(judge_results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Judge results saved to judge_results.json")

    # Step 4: Load manual labels if exist
    labels_path = os.path.join(BASE_DIR, "manual_labels.json")
    if os.path.exists(labels_path):
        with open(labels_path) as f:
            manual_labels = json.load(f)
        print("\n📊 Step 3: Calculating agreement...")
        agreement = calculate_agreement(judge_results, manual_labels)

        # Save calibration report
        report = {
            "date": "2026-05-01",
            "total_cases": len(CALIBRATION_CASES),
            "agreement": agreement,
            "quality_gate": "≥ 80% agreement",
            "passed": agreement["overall_pass"]
        }
        report_path = os.path.join(BASE_DIR, "calibration_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print(f"CALIBRATION RESULTS")
        print(f"{'='*60}")
        print(f"Overall agreement: {agreement['overall_agreement_rate']*100:.0f}%")
        print(f"Quality Gate (≥80%): {'✅ PASSED' if agreement['overall_pass'] else '❌ FAILED'}")
        print(f"\nBy judge:")
        for name, data in agreement["by_judge"].items():
            gate = "✅" if data["pass_gate"] else "❌"
            print(f"  {name:<15} {data['agreement_rate']*100:.0f}% ({data['agreements']}/{data['total']}) {gate}")

        return report
    else:
        print(f"\n⚠️  manual_labels.json not found.")
        print(f"Next step: review judge_results.json and create manual_labels.json")
        print(f"Format: {{\"cal_001\": {{\"groundedness\": \"PASS\", \"usefulness\": \"PASS\", \"correctness\": \"PASS\"}}, ...}}")
        return judge_results


if __name__ == "__main__":
    run_calibration()

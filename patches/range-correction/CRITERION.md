# The passive force criterion, and how we propose to check it

September 18, 2026. This governs `patches/range-correction/`.

## What changed and why

With `range` at MuJoCo's default 0.75 to 1.05 on all 44 muscles, no muscle was ever stretched past 1.05 of optimal length, so passive force never appeared. The old check, that no muscle carries passive force above a tenth of its declared peak, passed trivially. It was measuring the absence of a stretch rather than the absence of a defect.

Correcting `range` so that muscles weaken as they stretch necessarily reintroduces passive force, because that is what a stretched muscle does. So the old check now fails and needs replacing rather than satisfying.

## What we measured

Over postures the hand can hold, after the correction:

| | count |
|---|---|
| above a tenth of declared peak somewhere in their travel | 38 of 44 |
| above it at the median reachable posture | 2 of 44 |
| above it at the model's default posture | 17 of 44 |

The default posture is a flat fully extended hand, where the finger flexors and interossei sit 60 to 85 percent of the way up their own travel. So the tension sits at the ends of reach and at full extension, not where the hand works. That is the opposite distribution from the defect the original check was written for, which was a muscle acting as an uncommanded spring across its whole range: `LU_RB5` carried 120.60 N against a declared 47.90 N before correction.

Measured by `passive_where_it_actually_sits_2026-09-12.py`, output in this directory.

## What we propose

Read the count at the median reachable posture, which is 2 of 44, with a named exception for the finger flexors and interossei at full extension.

It still catches the original defect, since a muscle behaving like a spring carries tension where the hand works and not only at the extremes. Against it: a median is a weaker instrument than a maximum, and this criterion has not yet caught anything.

## The external check, which is the part we are least sure of

We would rather calibrate against measured hands than against a threshold we chose, and there is a source that may do it.

Wagner, Ch. (1988), "The pianist's hand: anthropometry and biomechanics," *Ergonomics* 31(1), 97-131. He measured 127 male and 111 female professional pianists: 20 hand dimensions, 17 ranges of active movement, and 11 characteristics of passive joint mobility. The passive measurements were made with the palm fixed and the subject consciously relaxed, recording joint displacement under a stated torque:

- thumb abduction: 25 Ncm, 4 N applied at the interphalangeal joint
- abduction of fingers 2 to 5: 25 Ncm, 7 N at the proximal interphalangeal joint
- combined hyperextension of MCP joints 2 to 5: 75 Ncm, 16.7 N at proximal interphalangeal joints 2 and 4

He names the derived quantity joint resistance. The apparatus is described in Wagner 1974a and 1974b.

The proposed test: apply 0.25 Nm to the model's thumb carpometacarpal abduction from a relaxed posture, measure the displacement, and compare it to his distribution. The same for finger abduction. That asks whether the model's passive resistance is in the human range rather than whether it clears a number we picked.

Two limits we can see. Joint resistance is everything crossing the joint, muscle and tendon and capsule and ligament and skin, so it caps what the muscles alone should contribute rather than giving them a target. And Wagner states that his measured abduction angles do not correspond to true joint angles, because the apparatus pivot sat between the two adjacent joints, so the resistances transfer and the angles do not.

His active ranges are useful separately. The reachable posture set the criterion is read over is currently bounded by the model's declared joint limits, and those contain large self-collision regions, 9 of 13 swept angles for the middle finger. Bounding it by measured human range instead would be better.

## What we would like to know

Whether this is the right reference, or whether there is a better one we have missed. Whether the comparison is sound given that the model's passive force is one contributor to a quantity Wagner measured whole. And whether the criterion should be a count at all, rather than something read off the force-length curve directly.

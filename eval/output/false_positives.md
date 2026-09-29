# False-positive examples (threshold=0.92)

These are labeled `should_miss` pairs. If similarity is above the operating
threshold they are true false positives; otherwise they are the nearest misses
the model almost confused.

## miss-029 (near_miss, similarity=0.9518, FALSE POSITIVE)

- **Cached prompt:** Recommend a weekend trip from Boston under $200.
- **Incoming prompt:** Recommend a weekend trip from Boston under $2000.
- **Why it's wrong:** Budget off by 10x still looks like the same travel query.

## miss-038 (near_miss, similarity=0.9481, FALSE POSITIVE)

- **Cached prompt:** Write a unit test for a Python function that adds two numbers.
- **Incoming prompt:** Write a unit test for a Python function that multiplies two numbers.
- **Why it's wrong:** Add vs multiply is a one-token swap; nomic still scores ~0.95 because the rest of the sentence is identical.

## miss-023 (near_miss, similarity=0.9067, near miss)

- **Cached prompt:** How can I reduce blue light from my monitor at night?
- **Incoming prompt:** How can I reduce brightness from my monitor at night?
- **Why it's wrong:** Blue light vs brightness: same 'reduce X from monitor at night' frame, different knob.

## miss-032 (near_miss, similarity=0.9034, near miss)

- **Cached prompt:** Explain overfitting in machine learning.
- **Incoming prompt:** Explain underfitting in machine learning.
- **Why it's wrong:** Overfitting vs underfitting are adjacent ML terms with opposite diagnoses.

## miss-020 (near_miss, similarity=0.8971, near miss)

- **Cached prompt:** How do I change a flat bicycle tire?
- **Incoming prompt:** How do I change a flat car tire?
- **Why it's wrong:** Bicycle vs car tire — shared 'change a flat * tire' template.

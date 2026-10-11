# Post-hoc technique comparison protocol, frozen before new fit

October11 2026. Same official752events/2887rows and frozen Stage3 membership.
2017+sets have now been viewed, so results are exploratory comparisons, not a new
independent confirmation. No synthetic/augmented evaluation data. Same2013calibration
and2014threshold set, no test-driven threshold/model tuning.

One prespecified comparison: HistGradientBoostingClassifier max_iter100,
learning_rate0.05,max_leaf_nodes7,l2_regularization1,min_samples_leaf20,
random_state42, early_stoppingFalse; class-balanced training sample weights only.
Add maximum daily rain within preceding14days and antecedent precipitation index
sum(rain_day*0.85^age) from the exact cached past-only ERA5 window. These are
literature-style diagnostic transformations, not established regional triggers.
0.85fixed beforehand, not tuned. No new rows, labels or terrain values.
Fit training only, Platt on2013 only, highest2014threshold with90%recall/<=10%FPR.
Screen criteria unchanged. Report all failures. Never choose a model on test scores
and market those same scores as unbiased. New geographic/prospective confirmation
will be necessary even if this comparative screen clears. Independent warning gates
unchanged. Pretrained NASA use awaits license/input/training-overlap resolution.

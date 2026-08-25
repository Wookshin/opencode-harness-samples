# Why Small Pull Requests Win

Most teams know that large pull requests are painful, but they keep creating them anyway. The reason is not laziness. It is that the cost of a large pull request is paid by the reviewer, while the cost of splitting one up is paid by the author. Incentives quietly push in the wrong direction.

A reviewer's attention is not a renewable resource within a single sitting. Studies of code review consistently find that defect detection drops sharply after roughly four hundred lines of changed code. Beyond that point, reviewers are not reading; they are skimming and approving. A two thousand line pull request does not get reviewed five times as thoroughly as a four hundred line one. It gets reviewed less thoroughly in absolute terms, because the reviewer gives up.

Small pull requests are also cheaper to revert. When a change is one focused commit, backing it out is a single operation with an obvious blast radius. When a change bundles a refactor, a bug fix, and a new feature, reverting it means choosing which of the three things you are willing to lose. Teams in that position usually choose to patch forward instead, which is how a small production incident becomes a long afternoon.

None of this requires new tooling. It requires a habit: before opening a pull request, ask whether the description needs the word "and". If it does, you probably have two pull requests.

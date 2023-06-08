# Canvas-Flexible-Assessment
This is an external Django application running on Canvas

# Testing Plan for New Changes
Whenever **Canvas** is bolded, this is a step to be done inside Canvas, otherwise it is within Flexible Assessment. I recommend you split tabs to quickly switch between Canvas and Flexible Assessment.
## Testing Canvas Integration
1. You can reset a course by deleting all the assessments and hitting submit
2. In **Canvas**, enable and open Flexible Assessment as an instructor
3. From **Canvas**, open Flexible Assessment as a student
4. Go to _Course Setup_, setup assessments and make sure 'Hide totals in student grades summary' correctly enables/disables the **Canvas** setting under _'More Options' > 'Hide totals in student grades summary'_
5. Inside **Canvas**, create assignment groups with at least one assignment inside, grade some students
6. Go to _Final Grades_, and match assignment groups
7. Inside **Canvas**, check that the assignment group percentages now match those in Flexible Assessment
8. On the _Final Grades_ page, double check that the grades matches **Canvas** Gradebook
9. Update some student choices so some override totals are different. 
10. Click on 'Submit Grades to Canvas' button
11. Should not be able to submit grades if **Canvas** setting under _'Grades' > 'Advanced' > 'Allow final grade override'_ is unchecked. (If you don't see this setting, check **Canvas** _'Settings' > 'Feature Options' > 'Final Grade Override'_)
12. Check **Canvas** Gradebook that override grades are sent correctly
13. From student perspective, **Canvas** grades should not be visible
14. Uncheck 'Hide totals in student grades summary' then submit grades to Canvas again
15. Student should now be able to see their overridden grade on **Canvas**
16. Delete an assignment group in **Canvas**
17. Rematch different assignment groups then submit grades to Canvas again

## Testing Core Features inside Flexible Assessment
As long as tests are maintained for new features created, the following checks are already unit tested. All of these steps are within Flexible Assessment. I recommend you open two separate browsers, one for the instructor, and one for the student view (You can't use the same browser window due to cookies and authentication).

1. Student: Check student view before instructor has setup a course
2. Instructor: Setup assessments and place open date in the future
3. Student: Check that student view homepage has been updated, but they should not be able to make changes
4. Instructor: Change Open date to a time in the past, also set Welcome Instructions and Comment Instructions
5. Student: Choose assessment weights as a student, and try going back to update the chosen weights
6. Instructor: Verify that student choices are received then set Close date to a time in the past
7. Student: Student should no longer be able to make changes
8. Instructor: Delete or add an assessment. Check that all student choices are reset, set Close date to the future
9. Student: Make new choices
10. Instructor: Change assessment ranges so that some student choices are now invalid. Verify that those students choices are reset, but valid ones remain.
11. Instructor: Go to _Student Choices_ and manually change a student's choices
12. Instructor: Go to _Final Grades_ and double check the exported csv is correct. Also check the _Change Log_.



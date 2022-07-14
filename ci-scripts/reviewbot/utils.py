import re
import os
from datetime import date
from hackmd import get_note, update_note


def add_new_review(review, content):
    today = date.today()
    date_syntax = today.strftime("%b %d, %Y") + "\n"  # todo: change to regex
    # Check if review is present at all
    is_review_present = re.search(re.escape(review), content)
    # Check if review is persent under current date
    if is_review_present:
        # Section of note after the last H2 heading before the review
        section_of_note = content.split(review)[0].split("\n## ")[-1]
        index = section_of_note.find(date_syntax)
        if index == -1:
            is_review_present = False
    if not is_review_present:
        date_heading = "## " + today.strftime("%b %d, %Y") + "\n"
        index = content.find(date_heading)
        # If no entry for today's date
        if index == -1:
            # Check if we have tags
            is_tags = re.search("tags: `.*`\n", content)
            if is_tags:
                # Insert new date after tags
                date_index = is_tags.regs[0][1]
            else:
                # Check if we have heading
                is_title = re.search("^#[ \t]+.*\n", content)
                if is_title:
                    # Insert new date after main heading
                    date_index = is_title.regs[0][1]
                else:
                    # idk, insert at the beginning?
                    date_index = 0
            new_content = content[:date_index] + "\n" + date_heading +\
                          '\n* ' + review + "\n" + content[date_index:]
            return new_content
        new_content = content[:(index + len(date_heading))] + '\n* ' + review + "\n" \
                      + content[(index + len(date_heading)):]
        return new_content
    print("Review is already present.")
    return content


def write_to_destination(review):
    note_id = os.getenv("note_id")
    content = get_note(note_id)
    if content is not None:
        new_content = add_new_review(review, content)
        result = update_note(note_id, new_content)
        return result
    return None

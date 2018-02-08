# This is a reddit bot!
# It's purpose is to provide definitions of rarely used words in order to make people smarter
# Written by \u\dito49 with help from the guide created by \u\kindw

# Changelog v0.4.1.4

# Changes:
    # Removed import bs4 (unused)
    # Added a line to empty the comments_read.txt file when new dictionaries have to be created
    # Added a segment to skip single letters and words with numbers in build_dictionary
    # Moved sub-count and over18 checks into write_comment to vastly speed up the process of building
        # Without sub-count, comments are on average 0.7 seconds faster
    # Moved 'if not building' before 'if comment in...' in build_dictionary
        # Python won't have to check 'if comment in...' if not building (it would if it were first)
    # Rewrote downvote_to_remove to remove local file requirement
    # Rewrote exception for ratelimit to be a little better
    # Improved comments

import praw
import requests
import re
from bs4 import BeautifulSoup
import time
import pickle

path = "c:\\users\\Colby\\PycharmProjects\\RareWordBot\\"


def file_import(filename):  # Gets dictionaries from disk
    with open(path + filename, 'rb') as f:
        variable_name = pickle.load(f)
        return variable_name


def file_export(filename, variable_name):  # Saves the dictionaries to the disk
    with open(path + filename, 'wb') as f:
        pickle.dump(variable_name, f)


def authenticate():  # Authenticates with reddit
    print 'Authenticating with Reddit...'
    reddit = praw.Reddit('RareWordBot', user_agent='RareWordBot v0.4.1.4 by /u/dito49')
    print 'Done.\n'
    return reddit


def fetch_definition(word):  # Searches dictionary.com for definitions of words

    url = 'http://www.dictionary.com/browse/%s?s=t' % word
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')

    tag = 0
    tags = soup.find_all('script')
    for tag in tags:
        try:
            if tag['type'] == "text/javascript":
                if tag.contents:
                    if 'var src' in tag.contents[0].decode("unicode-escape"):
                        for i in range(10):
                            tag = tag.next_sibling
                        break
            else:
                continue
        except KeyError:
            continue
    definition = str(tag)

    # Gets rid of some of the technical aspects of the definition tag to make a nice, pretty definition
    definition = definition.replace('<meta content=\"', '')
    definition = definition.replace(' See more." name=\"description\"/>', '')
    definition = definition.replace('1 .', '')  # Some have footnotes

    # At this point, definition looks like 'Pizza definition, delicious food when hot or cold'

    # Gets the provided word (Pizza) and 'definition, ' out of the definition
    definition = definition.replace(re.search('^(.*?) definition, ', definition).group(1)
                                    + ' definition, ', '', 1)

    # Gets the root word (ex. 'Pizza', if word == 'Pizzas')
    try:
        tags = soup.find_all('div')
        for tag in tags:
            try:
                if tag['class'] == [u'deep-link-synonyms']:
                    break
                else:
                    continue
            except KeyError:
                continue
        root = str(tag.contents[1])
        root = root.replace('<a data-linkid="oowy0r" href="http://www.thesaurus.com/browse/', '')
        root = root.replace('">See more synonyms on Thesaurus.com</a>', '')
    except IndexError:
        root = re.search('^(.*?) definition, ', definition).group(1)

    # If the root word is not the word in the comment, equate them
    if root.lower() != word.lower():
        equivs[word] = root

    return definition, root


def build_dictionary(reddit, subreddits, n, building):  # n = number of comments to be retrieved

    global nc
    for sub in subreddits:

        for comment in reddit.subreddit(sub).comments(limit=n):
            comments_read_r = open(path + 'comments_read.txt', 'r')
            if not building or (building and comment.id not in comments_read_r.read().splitlines()):
                comments_read_r.close()

                # Marks the comment as read
                comments_read_w = open(path + 'comments_read.txt', 'a+')
                comments_read_w.write(comment.id + '\n')
                comments_read_w.close()

                nc += 1

                word_list = url_remover(comment.body.lower())
                for word in word_list:

                    if len(word) == 1 or any(char.isdigit() for char in word):
                        continue

                    elif word in notWords:  # If we know it's not a word:
                        notWords[word] += 1

                    elif word in mainDict:  # If we know it's a word and it's a root
                        if mainDict[word][0] <= 2 and not building:
                            write_comment(word, comment, mainDict[word][1], reddit)
                        mainDict[word][0] += 1

                    elif word in equivs:  # If we know it's a word, but not a root
                        true_word = equivs[word]
                        if mainDict[true_word][0] <= 2 and not building:
                            write_comment(true_word, comment, mainDict[true_word][1], reddit)
                        mainDict[true_word][0] += 1

                    else:  # See if it's a word
                        try:
                            definition, true_word = fetch_definition(word)
                            if not building:
                                write_comment(true_word, comment, definition, reddit)
                            mainDict[true_word] = [1, definition]

                        except AttributeError:  # Raised by word = re.search....group(1)
                            notWords[word] = 1

            else:
                comments_read_r.close()

        file_export('RareWordBot_Dictionary', mainDict)  # Updates the dictionaries after n comments
        file_export('RareWordBot_Undictionary', notWords)
        file_export('RareWordBot_Equivalents', equivs)


def url_remover(text):

    # Gets location of common url indicators within a comment and deletes up to the next 'space'
    url_possibilities_start = ['https:', 'http:', 'www.', 'bit.']
    url_possibilities_end = ['.com', '.org', '.gov', '.uk']
    for key in url_possibilities_start + url_possibilities_end:
        while key in text:

            # Deletes beginning to end of url
            if key in url_possibilities_start:
                url_start = int(re.search(key, text).start())
                while True:
                    try:
                        if text[url_start] != ' ':
                            text = text[:url_start] + text[url_start + 1:]
                        else:
                            break
                    except IndexError:
                        break

            # Deletes end to beginning of url
            elif key in url_possibilities_end:
                url_end = int(re.search(key, text).end()) - 1
                while True:
                    if text[url_end] != ' ':
                        text = text[:url_end] + text[url_end + 1:]
                        url_end -= 1
                    else:
                        break

        # Splits up the remaining words into a list
        word_list = re.sub("[^\w]", " ", text).split()
        return word_list


def write_comment(word, comment, definition, reddit):

    url = 'http://www.dictionary.com/browse/%s?s=t' % word
    footer = '\n*****\n ^^| ^^I ^^am ^^a ^^bot ^^| ' \
             '^^[Problem?](https://www.reddit.com/r/RareWordBot/comments/6wdo4v/problems/) ^^| ' \
             '^^[Suggestions?]' \
             '(https://www.reddit.com/r/RareWordBot/comments/6wdjgf/miscellaneous_suggestions_or_comments/)' \
             ' ^^| ^^Other ^^definitions ^^at ^^[Dictionary.com](%s) ^^|' \
             ' ^^Downvote ^^to  ^^remove ^^|' % url

    # Will comment unless:
        # Subreddit has less than 250,000 subs or is over18
        # Comment has already been replied to
        # The bot wrote it

    if reddit.subreddit(str(comment.subreddit)).subscribers < 250000 or comment.subreddit.over18\
            or comment.author == 'RareWordBot':
        return

    comments_replied_r = open(path + 'comments_replied.txt', 'r')

    try:
        if comment.id not in comments_replied_r.read().splitlines():
            header = '\nLooks like \'%s\' is a rare word!\n' % word
            definition = '\n%s: %s\n' % (word, definition)
            comment.reply(header + definition + footer)
            comments_replied_r.close()

            with open(path + 'comments_replied.txt', 'a+') as comments_replied_w:
                comments_replied_w.write(comment.id + '\n')
                comments_replied_w.close()

            print 'Commenting: %s is an uncommon word\n' % word

    except praw.exceptions.APIException as error:  # Ratelimit error (posting too much)
        error = str(error)
        number, sleep_time = 0, 0
        print 'Error: Ratelimit exceeded\n'

        for letter in error:  # Searches the error for a number (will always be single digit)
            if letter.isdigit():
                number = letter
                break

        if 'minute' in error:  # Converts minute(s) to seconds
            sleep_time = ((int(number) + 1) * 60)

        if 'seconds' in error:
            sleep_time = int(number)

        print 'Sleeping for %d seconds\n' % sleep_time
        time.sleep(sleep_time)
        print 'I\'m back!'


def downvote_to_remove(reddit):
    for comment in reddit.redditor('RareWordBot').comments.new():
        if comment.score <= -2:
            comment.delete()


def run_rarewordbot():
    reddit_instance = authenticate()

    while nc < 1000000:  # Until 1,000,000 comments have been read, still building (won't comment)
        start = time.time()
        build_dictionary(reddit_instance, ['all'], 100, True)
        print '%s comments done (%s seconds)' % (nc, str(round(time.time() - start, 2)))
        time.sleep(1)

    whitelist = ['all']

    print 'Commence comments!\n'

    while True:  # Main function
        build_dictionary(reddit_instance, whitelist, 100, False)
        downvote_to_remove(reddit_instance)
        print 'Batch done. Waiting. \n'
        time.sleep(5)
        print 'Resuming. \n'


try:
    mainDict = file_import('RareWordBot_Dictionary')
    notWords = file_import('RareWordBot_Undictionary')
    equivs = file_import('RareWordBot_Equivalents')
    print 'Using existing dictionaries\n'

except IOError:  # The dictionaries aren't on disk
    mainDict = {}
    notWords = {}
    equivs = {}
    open(path + 'comments_read.txt', 'w').close()
    print 'Creating new dictionaries\n'

nc = 0
with open(path + 'comments_read.txt', 'r') as read_total:
    for line in read_total:
        nc += 1

run_rarewordbot()

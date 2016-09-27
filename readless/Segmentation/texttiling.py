#!/usr/bin/python

# *****************************************************************************
#
# Author: Aditya Chatterjee
#
# Interweb/ contacts: GitHub.com/AdiChat
#                     Email: aditianhacker@gmail.com
#
# Implementation of the TextTiling Algorithm
#
# MIT License
#
# To keep up with the latest version, consult repository: GitHub.com/AdiChat/Read-Less
#
# To get an overview of the TextTiling Algorithm, consult wiki: Github.com/AdiChat/Read-Less/wiki/TextTiling
#
# *****************************************************************************

from __future__ import division
import re
import sys
import numpy as np
import os
import glob
from math import sqrt
from collections import Counter
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import stopwords
from nltk.corpus import brown

lemmatizer = WordNetLemmatizer()
stop_words = stopwords.words('english')

def tokenize_string(input_string, w):
    '''
    Tokenize a string using the following four steps:
        1) Turn all text into lowercase and split into tokens by
           removing all punctuation except for apostrophes and internal
           hyphens
        2) Remove stop words 
        3) Perform lemmatization 
        4) Group the tokens into groups of size w, which represents the 
           pseudo-sentence size.
 
    Arguments :
        input_string : A string to tokenize
        w: pseudo-sentence size

    Returns:
        A tuple (token_sequences, unique_tokens, paragraph_breaks), where:
            token_sequences: A list of token sequences, each w tokens long.
            unique_tokens: A set of all unique words used in the text.
            paragraph_breaks: A list of indices such that paragraph breaks
                              occur immediately after each index.
    '''

    tokens = []
    paragraph_breaks = []
    token_count = 0
    token_sequences = []
    index = 0  
    count = Counter() 

    # split text into paragraphs
    paragraphs = [s.strip() for s in input_string.splitlines()]
    paragraphs = [s for s in paragraphs if s != ""]

    pattern = r"((?:[a-z]+(?:[-'][a-z]+)*))" # For hyphen seperated words

    # Count number of tokens - words and words seperated by hyphen
    for paragraph in paragraphs:
        paragraph_tokens = re.findall(pattern, paragraph)
        tokens.extend(paragraph_tokens)
        token_count += len(paragraph_tokens)
        paragraph_breaks.append(token_count)

    paragraph_breaks = paragraph_breaks[:-1]

    # split tokens into groups of size w
    for i in xrange(len(tokens)):
        count[tokens[i]] += 1
        index += 1
        if index % w == 0:
            token_sequences.append(count)
            count = Counter()
            index = 0

    # remove stop words from each sequence
    for i in xrange(len(token_sequences)):
        token_sequences[i] = [lemmatizer.lemmatize(word) for word in token_sequences[i] if word not in stop_words]

    # lemmatize the words in each sequence
    for i in xrange(len(token_sequences)):
        token_sequences[i] = [lemmatizer.lemmatize(word) for word in token_sequences[i]]

    # get unique tokens
    unique_tokens = [word for word in set(tokens) if word not in stop_words] 

    return (token_sequences, unique_tokens, paragraph_breaks)

def vocabulary_introduction(token_sequences, w):
  """
  Computes lexical score for the gap between pairs of text sequences.
  It starts assigning scores after the first sequence.

  Args:
    w: size of a sequence

  Returns:
    list of scores where scores[i] corresponds to the score at gap position i that is the score after sequence i.

  Raises:
    None
  """
  # stores the tokens in the previous sequence
  new_words1 = set()
  # stores the tokens in the next sequence
  new_words2 = set(token_sequences[0])
  # score[i] corresponds to gap position i
  scores = []
  w2 = w * 2

  for i in xrange(1,len(token_sequences)-1):
    # new words to the left of the gap
    new_words_1 = set(token_sequences[i-1]).difference(new_words1)

    # new words to the right of the gap
    new_words_2 = set(token_sequences[i+1]).difference(new_words2)

    # calculate score and update score array
    score = (len(new_words_1) + len(new_words_2)) / w2
    scores.append(score)

    # update sets that keep track of new words
    new_words1 = new_words1.union(token_sequences[i-1])
    new_words2 = new_words2.union(token_sequences[i+1])

  # special case on last element
  b1 = len(set(token_sequences[len(token_sequences)-1]).difference(new_words1))
  scores.append(b1/w2)
  return scores


def block_score(k, token_sequence, unique_tokens):
    """
    Computes the similarity scores for adjacent blocks of token sequences.
    Args:
        k: the block size
        token_seq_ls: list of token sequences, each of the same length
        unique_tokens: A set of all unique words used in the text.
    Returns:
        list of block scores from gap k through gap (len(token_sequence)-k-2) both inclusive.
    Raises:
        None.
    """
    score_block = []
    before_count = Counter()
    after_count = Counter()

    # calculate score for each gap with at least k token sequences on each side
    for gap_index in range(1, len(token_sequence)):
        current_k = min(gap_index, k, len(token_sequence) - gap_index)
        before_block = token_sequence[gap_index - current_k : gap_index]
        after_block = token_sequence[gap_index : gap_index + current_k]
        
        for j in xrange(current_k):
            before_count = before_count + Counter(token_sequence[gap_index + j - current_k])
            after_count = after_count + Counter(token_sequence[gap_index + j])
        
        # calculate and store score
        numerator = 0.0
        before_sum = 0.0
        after_sum = 0.0

        for token in unique_tokens:
            numerator = numerator + (before_count[token] * after_count[token])
            before_sum = before_sum + (before_count[token] ** 2)
            after_sum = after_sum + (after_count[token] ** 2)

        denominator = sqrt(before_sum * after_sum)

        if denominator == 0:
            denominator = 1

        score_block.append(numerator / denominator)

    return score_block

def getDepthCutoff(lexScores, liberal=True):
    """
    Compute the cutoff for depth scores above which gaps are considered boundaries.

    Args:
        lexScores: list of lexical scores for each token-sequence gap
        liberal: True IFF liberal criterion will be used for determining cutoff

    Returns:
        A float representing the depth cutoff score

    Raises:
        None
    """
    mean = np.mean(lexScores)
    stdev = np.std(lexScores)
    return mean - stdev if liberal else mean - stdev / 2

def getDepthSideScore(lexScores, currentGap, left):
    """
    Computes the depth score for the specified side of the specified gap
    Args:
        lexScores: list of lexical scores for each token-sequence gap
        currentGap: index of gap for which to get depth side score
        left: True IFF the depth score for left side is desired
    Returns:
        A float representing the depth score for the specified side and gap,
        calculated by finding the "peak" on the side of the gap and returning
        the difference between the lexical scores of the peak and gap.
    Raises:
        None
    """
    depthScore = 0
    i = currentGap
    # continue traversing side while possible to find new peak
    while lexScores[i] - lexScores[currentGap] >= depthScore:
        # update depth score based on new peak
        depthScore = lexScores[i] - lexScores[currentGap]
        # go either left or right depending on specification
        i = i - 1 if left else i + 1
        # do not go beyond bounds of gap!
        if (i < 0 and left) or (i == len(lexScores) and not left):
            break
    return depthScore

def getGapBoundaries(lexScores):
    """
    Get the gaps to be considered as boundaries based on gap lexical scores
    Args:
        lexScores: list of lexical scores for each token-sequence gap
    Returns:
        A list of gaps (identified by index) that are considered boundaries.
    Raises:
        None
    """
    boundaries = []
    cutoff = getDepthCutoff(lexScores)

    for i, score in enumerate(lexScores):
        # find maximum depth to left and right
        depthLeftScore = getDepthSideScore(lexScores, i, True)
        depthRightScore = getDepthSideScore(lexScores, i, False)

        # add gap to boundaries if depth score beyond threshold
        depthScore = depthLeftScore + depthRightScore
        if depthScore >= cutoff:
            boundaries.append(i)
    return boundaries

def getBoundaries(lexScores, pLocs, w):
    """
    Get locations of paragraphs where subtopic boundaries occur
    Args:
        lexScores: list of lexical scores for each token-sequence gap
        pLocs: list of token indices such that paragraph breaks occur after them
        w: number of tokens to be grouped into each token-sequence
    Returns:
        A sorted list of unique paragraph locations (measured in terms of token
        indices) after which a subtopic boundary occurs.
    Raises:
        None
    """
    # do not allow duplicates of boundaries
    parBoundaries = set()
    # convert boundaries from gap indices to token indices
    gapBoundaries = getGapBoundaries(lexScores)
    tokBoundaries = [w * (gap + 1) for gap in gapBoundaries]

    # convert raw token boundary index to closest index where paragraph occurs
    for i in xrange(len(tokBoundaries)):
        parBoundaries.add(min(pLocs, key=lambda b: abs(b - tokBoundaries[i])))

    return sorted(list(parBoundaries))

def writeTextTiles(boundaries, pLocs, inputText, outfile):
    """
    Get TextTiles in the input text based on paragraph locations and boundaries.
    Args:
        boundaries: list of paragraph locations where subtopic boundaries occur
        pLocs: list of token indices such that paragraph breaks occur after them
        inputText: a string of the initial (unsanitized) text
    Returns:
        A list of indicies of section breaks. Index i will be in this list if
        there is a topic break after the ith paragraph. 
    Raises:
        None
    """
    textTiles = []
    paragraphs = [s.strip() for s in inputText.splitlines()]

    paragraphs = [s for s in paragraphs if s != ""]

    print len(paragraphs)
    #print paragraphs
    print len(pLocs)

    #assert len(paragraphs) == len(pLocs) + 1
    splitIndices = [pLocs.index(b) + 1 for b in boundaries]

    startIndex = 0
    # append section between subtopic boundaries as new TextTile
    for i in splitIndices:
        textTiles.append(paragraphs[startIndex:i])
        startIndex = i
    # tack on remaining paragraphs in last subtopic
    textTiles.append(paragraphs[startIndex:])
    
    f = open(outfile, 'w')
    for i, textTile in enumerate(textTiles):
        f.write('SUB-TOPIC:' + str(i+1) + '\n')
        f.write('----------\n\n')
        for paragraph in textTile:
            f.write(paragraph + '\n\n')
      
    return splitIndices

def run(outfile, data, w, k):
    """
    Helper function that runs the TextTiling on the entire corpus
    for a given set of parameters w and k, and writes the average 
    statistics to outfile. The corpus is assumed to live in the "articles"
    directory, which must be in the same folder as this python file.
    Args:
        outfile: the name of the output file
        w: pseudo-sentence size.
        k: length of window as defined in the paper.
        data: input string
    Returns:
        None
    Raises:
        None.
    """
    out = open(outfile, 'a')
    out.write("w = " + str(w) + ", k = " + str(k) + "\n")

    counter = 0
    print "processing input " 
               
    text = data;

    # 1) do our block comparison and 2) vocabulary introduction
    token_sequences, unique_tokens, paragraph_breaks = tokenize_string(text, w)
    out1 = open("outfile1.txt", 'a')
    for tile in token_sequences:
        out1.write("\n----------------------------------------------------------------------------------------\n")
        out1.write("\nNEW SEQUENCE\n")
        for tile1 in tile:
            out1.write(tile1)
            out1.write(" ; ")
            
    scores1 = block_score(k, token_sequences, unique_tokens)
    scores2 = vocabulary_introduction(token_sequences, w)
    boundaries1 = getBoundaries(scores1, paragraph_breaks, w)
    boundaries2 = getBoundaries(scores2, paragraph_breaks, w)
    pred_breaks1 = writeTextTiles(boundaries1, paragraph_breaks, text, outfile)
    pred_breaks2 = writeTextTiles(boundaries2, paragraph_breaks, text, outfile)

    num_pgraphs = len(paragraph_breaks)
    boundaries1 = getBoundaries(scores1, paragraph_breaks, w)
    writeTextTiles(boundaries1, paragraph_breaks, text, "outfile.txt")

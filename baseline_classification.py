# ------------------------------------
# OrchideaSOL classification baselines
# ------------------------------------
#
# Written by Carmine E. Cella, 2020
#
# This code is distributed with the OrchideaSOL dataset
# of extended instrumental techniques.
#
# For more information, please see:
# C. E. Cella, D. Ghisi, V. Lostanlen, F. Lévy, J. Fineberg and Y. Maresz,
#       OrchideaSOL: a dataset of extended instrumental techniques for computer-assisted orchestration,
#       ICMC 2020, Santiago, Chile.
#

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.decomposition import PCA
from sklearn.model_selection import cross_val_score
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import KFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from collections import Counter
from matplotlib import pyplot as plt

import librosa
import librosa.display
import json
import os
import random
import sys
from time import process_time

# raw dataset
# file hierarchy: (note that folders Brass, Winds, Strings are not present)
# ----TinySOL
#   ----Bn
#   ----Cb
#   ----Va
#   etc...
path = './TinySOL_0.6/TinySOL'

# time duration
time = 4

# number of samples between successive frames in librosa.melspectrogram
mel_hop_length = 44100


def mix(fa, fb):
    diff = len(fa) - len(fb)

    if diff > 0:
        add = np.zeros((1, diff), dtype=np.float32)
        fb = np.append(fb, add)
    elif diff < 0:
        add = np.zeros((1, -diff), dtype=np.float32)
        fa = np.append(fa, add)

    return fa+fb
    
def combine_sounds(soundlist):
    mixed_file = np.zeros((1, 1))
    sr = 0
    for sound in soundlist:
        sound_path = os
        sfile, sr = librosa.load(sound, sr=None)

        # mfcc = librosa.feature.mfcc(y=sfile, sr=sr, hop_length=mel_hop_length)
        # librosa.display.specshow(mfcc)
        # plt.title(sound)
        # plt.show()

        if len(sfile) > time*sr:
            # randomly select one part of the raw audio
            n = np.random.randint(0, len(sfile)-time*sr)
            sfile = sfile[n:n+time*sr]
        # add augment
        # sfile = wav_augment(sfile, sr)
        mixed_file = mix(mixed_file, sfile)
    mixed_file = mixed_file/len(soundlist)

    # mfcc = librosa.feature.mfcc(y=sfile, sr=sr, hop_length=mel_hop_length)
    # librosa.display.specshow(mfcc)
    # plt.title('mix')
    # plt.show()
    
    return [mixed_file, sr]

def calculate_features(sample, sr):
    feature = librosa.feature.mfcc(y=sample, sr=sr,
                                             hop_length=mel_hop_length)

    # zero padding
    expected_length = sr*time // mel_hop_length + 1
    diff = expected_length - feature.shape[1]
    if diff > 0:
        padding = np.zeros((feature.shape[0], diff), dtype=np.float32)
        feature = np.append(feature, padding)
    return feature

def create_binary_label(instruments, orchestra):
    '''
        given a list of instruments, return a binary vector whose length is the number
        of instruments in the orchestra
    '''
    label = np.zeros(len(orchestra), dtype=np.float32)
    for instrument in instruments:
        index = orchestra.index(instrument)
        label[index] = 1.0
    return label

def generate_data(orchestra, n, num_samples):
    '''
        create combinations of n instruments using only the instruments defined in 'orchestra'

    '''

    # dictionary where key is instrument name 
    # and value is a list of all the samples in the dataset for that instrument
    samples = {} 
    for instrument in orchestra:
        samples[instrument] = []
        instrument_path = os.path.join(path, instrument)
        for sample in os.listdir(instrument_path):
            sample_path = os.path.join(instrument_path, sample)
            samples[instrument].append(sample_path)

    X = [] # data
    y = [] # labels

    for i in range(num_samples):
        # select n instruments
        instruments = random.sample(orchestra, n)
        samples_to_combine = []
        # for each of n chosen instruments, randomly select one sample
        for instrument in instruments:
            sample = random.choice(samples[instrument])
            samples_to_combine.append(sample)

        # combine sounds, storing combined sound in `mixture`
        mixture, sr = combine_sounds(samples_to_combine)
        # calculate feature of combined sound
        features = calculate_features(mixture, sr)
        # create label from the instruments that were chosen
        label = create_binary_label(instruments, orchestra)

        # since you cant know the dimensions until the features have been computed,
        # you can't make the ndarray until now
        if i == 0:
            num_features = features.flatten().shape[0]
            X = np.zeros((num_samples, num_features))
            y = np.zeros((num_samples, label.shape[0]))
        
        X[i] = features.flatten()
        y[i] = label

        if i % 100 == 0:
            print("{} / {} have finished".format(i, num_samples))

    return X, y


def train_and_test(X, y):

    X_train, X_test, y_train, y_test = train_test_split(X,
                                                    y,
                                                    test_size = 0.4,
                                                    random_state = 42,
                                                    shuffle=True)

    # print('X train: ', X_train.shape)
    # print('X test: ', X_test.shape)
    # print('y train: ', y_train.shape)
    # print('y test: ', y_test.shape)

    clfs = []

    clf = SVC(kernel='rbf')
    clf = MultiOutputClassifier(clf)
    clfs.append(clf)

    test_scores = []

    print ("\nRunning classifications...")
    for classifier in clfs:
        start_time = process_time()
        pipeline = Pipeline([
            ('normalizer', StandardScaler()),
            ('clf', classifier)
        ])
        print('---------------------------------')
        print(str(classifier))
        print('---------------------------------')
        shuffle = KFold (n_splits=5, random_state=5, shuffle=True)
        scores = cross_val_score (pipeline, X, y, cv=shuffle)

        print("model scores: ", scores)
        print("average training score: ", scores.mean ())

        pipeline.fit (X_train, y_train)
        ncvscore = pipeline.score(X_test, y_test)
        print("test accuracy: ", ncvscore)
        print("time: ", process_time() - start_time)
        test_scores.append(ncvscore)

    return test_scores

def make_plot(x, y):
    plt.plot(x, y, marker='o')
    for a, b in zip(x, y):
        if a < 3:
            placement = (20, -10)
        else:
            placement = (0, 10)
        plt.annotate(str(b),  # this is the text
                    (a, b),  # this is the point to label
                    textcoords="offset points",  # how to position the text
                    xytext=placement,  # distance from text to points (x,y)
                    ha='center')  # horizontal alignment can be left, right or center

    plt.ylim((0, 1))
    plt.xticks(range(1, max(x) + 1))

    plt.xlabel("Number of instruments combined")
    plt.ylabel("Accuracy")
    # plt.title("""Accuracy of non-linear SVM classifying various numbers of instrument combinations \n from an orchestra of 12 instruments using 50,000 samples per combination""")
    plt.title("classifier: non-linear SVM, classifying: instrument only, \n orchestra size: 12, number of samples: 50,000")
    plt.show()


orchestra = ['Vc', 'Fl', 'Va', 'Vn', 'Ob', 'BTb',
               'Cb', 'ClBb', 'Hn', 'TpC', 'Bn', 'Tbn']



# data = []
# labels = []
# num_samples = 50000
# scores = []

# for n in [1, 2, 3, 5, 10]:
#     X, y = generate_data(orchestra, n, num_samples)

#     score = train_and_test(X, y)[0]
#     scores.append(score)

#     print('---------------------------------')
#     print("orchestra size: ", len(orchestra))
#     print("n: ", n)
#     print("number of samples: ", num_samples)
#     print("scores from this run: ", score)
#     print('---------------------------------')

# print('*****************')
# print("All training complete")
# for n, score in zip([1, 2, 3, 5, 10], scores):
#     print("n: {}, score: {}".format(n, score))
# print('*****************')

make_plot([1, 2, 3, 5, 10], [0.998, 0.554, 0.166, 0.043, 0.005])

def make_plot_multiple_lines(all_scores):
    '''
    scores is a nested dictionary that maps a value of n to a dictionary of samples and scores
    '''
    for n in all_scores.keys():
        scores = all_scores[n]
        num_samples = list(scores.keys())
        accuracies = list(scores.values())

        plt.plot(num_samples, accuracies, label="combinations of {} instruments".format(n), marker='o')

        

        for x, y in scores.items():
            plt.annotate(str(y),  # this is the text
                        (x, y),  # this is the point to label
                        textcoords="offset points",  # how to position the text
                        xytext=(0, 10),  # distance from text to points (x,y)
                        ha='center')  # horizontal alignment can be left, right or center
    

    plt.ylim((0, 0.6))
    plt.legend()

    plt.xlabel("Number of samples used to train and test")
    plt.ylabel("Accuracy")
    plt.title("Accuracy of SVM classifying combinations of instruments".format(n))
    plt.show()

# two = {1000: 0.09, 10000: 0.38, 30000: 0.51, 50000: 0.55}
# three = {1000: 0.01, 10000: 0.117, 30000: 0.164, 50000: 0.193}
# four = {1000: 0.0075, 10000: 0.047, 30000: 0.066, 50000: 0.075}

# s = {2: two, 3: three, 4: four}
# make_plot_multiple_lines(s)


#eof

from keras.layers import Embedding, Bidirectional, LSTM, Dropout
from keras.preprocessing.sequence import pad_sequences
from keras_contrib.layers import CRF
from keras.models import Sequential
import matplotlib.pyplot as plt
from collections import Counter
import pickle
import numpy
import jieba
import csv

Label_Lst = ['O', 'B-ASP', 'I-ASP', 'B-OPI', 'I-OPI']  # 此处修改标签为本实验的标签
Train_Reviews = '../source/train_reviews.csv'  # 电商评论训练集源文件
Train_Labels = '../source/train_labels.csv'  # 电商评论训练集结果文件
Test_Reviews = '../source/test_reviews.csv'  # 电商评论测试集源文件
Test_Labels = '../source/test_labels.csv'  # 电商评论测试集结果文件
Tag_Train = '../data/train.data'  # 标注训练集文本
Tag_Test = '../data/test.data'  # 标注验证集文本
Max_Len = 50  # 训练集一行分词的最大词数
Embed_Dim = 100
Batches = 16
Epochs = 10
Units = 100


def get_data():  # 获取分词后的训练数据及其对应的标注
    review_dic, block_dic, idx2words, idx2labels = {}, {}, {}, {}
    with open(Train_Reviews, 'r', encoding='utf-8') as f_reviews:
        reviews = csv.reader(f_reviews)
        for line in reviews:
            if line[0] == 'id':
                continue
            review_dic[int(line[0])] = line[1]
            block_dic[int(line[0])] = {}
    with open(Train_Labels, 'r', encoding='utf-8') as f_labels:
        labels = csv.reader(f_labels)
        for line in labels:
            if line[0] == 'id':
                continue
            if line[1] != '_':
                block_dic[int(line[0])][int(line[2])] = (int(line[2]), int(line[3]), 'ASP')
            if line[4] != '_':
                block_dic[int(line[0])][int(line[5])] = (int(line[5]), int(line[6]), 'OPI')
    block_dic = {idx: {i: block_dic[idx][i] for i in sorted(block_dic[idx])} for idx in block_dic}
    for idx in block_dic:
        idx2words[idx], idx2labels[idx], l_num = [], [], 0
        for j in block_dic[idx]:
            l_words = jieba.lcut(review_dic[idx][l_num:j])
            idx2words[idx].extend(l_words)
            idx2labels[idx].extend(['O'] * len(l_words))  # 加上所有的O分词

            m_words = jieba.lcut(review_dic[idx][j:block_dic[idx][j][1]])
            idx2words[idx].extend(m_words)
            flag = block_dic[idx][j][2]  # 标识ASP或者OPI
            idx2labels[idx].extend(['B-' + flag])
            idx2labels[idx].extend(['I-' + flag] * (len(m_words) - 1))  # 加上全部的I-flag
            l_num = block_dic[idx][j][1]
        last_words = jieba.lcut(review_dic[idx][l_num:])  # 最后一个区块后面的所有分词
        idx2words[idx].extend(last_words)
        idx2labels[idx].extend(['O'] * len(last_words))
    return idx2words, idx2labels  # 形如{1:['挺','漂亮','的']},{1:['B-OPI','I-OPI','I-OPI']}


def load_data():
    idx2words, idx2labels = get_data()
    word_counts = Counter(word.lower() for idx in idx2words for word in idx2words[idx])
    vocab = [w for w, f in iter(word_counts.items()) if f >= 1]
    with open('../model/extract/word2vec.pkl', 'wb') as f:
        pickle.dump(vocab, f)
    word2idx = dict((word, idx) for idx, word in enumerate(vocab))
    x = pad_sequences([[word2idx[w.lower()] for w in idx2words[i]] for i in idx2words], Max_Len)
    y = pad_sequences([[Label_Lst.index(w) for w in idx2labels[i]] for i in idx2labels], Max_Len)
    y = numpy.expand_dims(y, 2)  # n*Max_Len*1
    return x, y, vocab


def create_model(train=True):
    if train:
        x, y, vocab = load_data()
    else:
        with open('../model/extract/word2vec.pkl', 'rb') as f:
            vocab = pickle.load(f)
    model = Sequential()
    model.add(Embedding(len(vocab) + 1, Embed_Dim, mask_zero=True, input_length=Max_Len))
    model.add(Bidirectional(LSTM(Units, return_sequences=True)))
    model.add(Dropout(0.5))
    crf = CRF(len(Label_Lst), sparse_target=True)
    model.add(crf)  # 添加crf层
    model.summary()  # 查看网络结构
    model.compile('adam', crf.loss_function, metrics=[crf.accuracy])
    if train:
        return model, x, y
    else:
        return model, vocab


def main():
    model, x, y = create_model()
    hist = model.fit(x, y, Batches, Epochs, validation_split=0.1)  # 训练集和验证集为9:1
    model.save('../model/extract/extract.h5')  # 保存模型
    plt.plot(range(Epochs), hist.history['val_crf_viterbi_accuracy'], label='val_acc')
    plt.show()


if __name__ == '__main__':
    main()

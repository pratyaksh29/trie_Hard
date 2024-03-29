import os
from tkinter import *
from bs4 import BeautifulSoup,SoupStrainer
import tkinter as tk
import urllib.request
import re
import collections
import pickle
import nltk
import pyttsx3
import ssl
from googletrans import Translator


lis=list(map(chr,range(97,123)))
lis.append("'")
word=''
class TrieNode:
   def __init__(self):
       self.val=None
       self.pointers={}
       self.end=0
class Trie:
   def __init__(self):
       self.root=TrieNode()
   def insert(self,word):
       self.recInsert(word,self.root)
       return
   def recInsert(self,word,node):
       if word[:1]not in node.pointers:
           newNode=TrieNode()
           newNode.val=word[:1]
           node.pointers[word[:1]]=newNode
           self.recInsert(word,node)
       else:
           nextNode=node.pointers[word[:1]]
           if len(word[1:])==0:
               node.end=1
               return
           return self.recInsert(word[1:],nextNode)
   def search(self,word):
       if len(word)==0:
           return False
       return self.recSearch(word,self.root)
   def recSearch(self,word,node):
       if word[:1]not in node.pointers:
           return False
       else:
           nextNode=node.pointers[word[:1]]
           if len(word[1:])==0:
               if nextNode.end==1:
                   return True
               else:
                   return False
           return self.recSearch(word[1:],nextNode)
   def startsWith(self,prefix):
       if len(prefix)==0:
           return True
       return self.recSearchPrefix(prefix,self.root)
   def recSearchPrefix(self,word,node):
       if word[:1]not in node.pointers:
           return False
       else:
           if len(word[1:])==0:
               return True
           nextNode=node.pointers[word[:1]]
           return self.recSearchPrefix(word[1:],nextNode)
   def findAll(self,node,word,sugg):
       for c in lis:
           if c in node.pointers:
               if node.pointers[c].end==1:
                   sugg.append(word+str(c))
               self.findAll(node.pointers[c],word+str(c),sugg)
       return
   def didUMean(self,word,sugg):
       if self.startsWith(word):
           top=self.root
           for c in word:
               top=top.pointers[c]
           self.findAll(top,word,sugg)
       else:
           return

trie = Trie()
try:
    with open('big.txt', 'r') as file:
        words = file.read().split()
    for word in words:
        trie.insert(word)
except FileNotFoundError:
    print("Warning: 'big.txt' file not found. Trie could not be initialized.")
# try:
#     trie = pickle.load(open("save.p", "rb"))
# except FileNotFoundError:
#     print("Warning: 'save.p' file not found. Trie data could not be loaded.")
#     trie = Trie()


# deleted save.p

def train(features):
   model=collections.defaultdict(lambda:1)
   for f in features:
       if model[f]>1 or trie.search(f):
           model[f]+=1
   return model
def words(text):
   return re.findall('[a-z]+',text.lower())
try:
   NWORDS=train(words(open('big.txt','r').read()))
except FileNotFoundError:
   print("Warning: 'big.txt' file not found. NWORDS could not be initialized.")
   NWORDS={}
class EditDist:
   def __init__(self):
       pass
   alphabet='abcdefghijklmnopqrstuvwxyz'
   def edits1(self,word):
       splits=[(word[:i],word[i:])for i in range(len(word)+1)]
       deletes=[a+b[1:]for a,b in splits if b and trie.search(a+b[1:])]
       transposes=[a+b[1]+b[0]+b[2:]for a,b in splits if len(b)>1 and trie.search(a+b[1]+b[0]+b[2:])]
       replaces=[a+c+b[1:]for a,b in splits for c in self.alphabet if b and trie.search(a+c+b[1:])]
       inserts=[a+c+b for a,b in splits for c in self.alphabet if trie.search(a+c+b)]
       return set(deletes+transposes+replaces+inserts)
   def knownEdits2(self,word):
       return set(e2 for e1 in self.edits1(word)for e2 in self.edits1(e1)if trie.search(e2))
   def known(self,words):
       return set(w for w in words if w in NWORDS)
   def correct(self,word):
       candidates=self.known([word])or self.known(self.edits1(word))or self.knownEdits2(word)or [word]
       sugg=list(candidates)
       sugg.sort(key=lambda s:nltk.edit_distance(word,s))
       return sugg[:min(len(sugg),10)]
def util(word):
   word=word.lower()
   output=""
   if trie.search(word):
       output+="Found\n"
       urlStr='http://www.dictionary.com/browse/'+word+'?s=t'
       ctx=ssl.create_default_context()
       ctx.check_hostname=False
       ctx.verify_mode=ssl.CERT_NONE
       url=urllib.request.urlopen(urlStr,context=ctx)
       content=url.read()
       soup=BeautifulSoup(content,features="html.parser")
       product=SoupStrainer('section',{'class':'def-pbk ce-spot'})
       main=[p.get_text(strip=True)for p in soup.find_all(product)]
       for item in main:
           sep=re.split('(\\d+)\\.',item)
           for th in sep:
               output+=th+"\n"
           output+="\n"
       chunks=[phrase for item in main for phrase in re.split('(\\d+)\\.',item)]
       res=[chunk for chunk in chunks if chunk]
       text='\n'.join(chunk for chunk in res)
       output+=text
   else:
       output+="Not Found\nDid You Mean:\n"
       ed=EditDist()
       sugg=[]
       trie.didUMean(word,sugg)
       if len(sugg)!=0:
           sugg = sorted(sugg, key=lambda s: nltk.edit_distance(word, s))
           output += '\n'.join(sugg[:min(len(sugg), 10)])
       else:
           sugg=ed.correct(word)
           sugg = sorted(sugg, key=lambda s: nltk.edit_distance(word, s))
           output += '\n'.join(sugg[:min(len(sugg), 10)])
   return output
class AutocompleteEntry(Entry):
   def __init__(self,*args,**kwargs):
       Entry.__init__(self,*args,**kwargs)
       self.var=self["textvariable"]
       if self.var=='':
           self.var=self["textvariable"]=StringVar()
       self.var.trace('w',self.changed)
       self.bind("<Right>",self.selection)
       self.bind("<Up>",self.up)
       self.bind("<Down>",self.down)
       self.lb_up=False
   def changed(self,name,index,mode):
       if self.var.get()=='':
           if self.lb_up:
               self.lb.destroy()
               self.lb_up=False
       else:
           words=self.comparison()
           if words:
               if not self.lb_up:
                   self.lb=Listbox()
                   self.lb.bind("<Double-Button-1>",self.selection)
                   self.lb.bind("<Right>",self.selection)
                   self.lb.place(x=self.winfo_x(),y=self.winfo_y()+self.winfo_height())
                   self.lb_up=True
               self.lb.delete(0,END)
               for w in words:
                   self.lb.insert(END,w)
           else:
               if self.lb_up:
                   self.lb.destroy()
                   self.lb_up=False
   def selection(self,event):
       if self.lb_up:
           self.var.set(self.lb.get(ACTIVE))
           self.lb.destroy()
           self.lb_up=False
           self.icursor(END)
   def up(self,event):
       if self.lb_up:
           if self.lb.curselection()==():
               index='0'
           else:
               index=self.lb.curselection()[0]
           if index!='0':
               self.lb.selection_clear(first=index)
               index=str(int(index)-1)
               self.lb.selection_set(first=index)
               self.lb.activate(index)
   def down(self,event):
       if self.lb_up:
           if self.lb.curselection()==():
               index='0'
           else:
               index=self.lb.curselection()[0]
           if index!=END:
               self.lb.selection_clear(first=index)
               index=str(int(index)+1)
               self.lb.selection_set(first=index)
               self.lb.activate(index)
   def comparison(self):
       word=self.var.get()
       word=word.lower()
       ed=EditDist()
       sugg=[]
       trie.didUMean(word,sugg)
       if len(sugg)!=0:
           sugg.sort(key=lambda s:len(s))
       else:
           sugg=ed.correct(word)
       res=[chunk for chunk in sugg[:min(len(sugg),10)]]
       return res
def showSearchResults():
    key = entry.get()
    word = key
    text = util(key)
    word_text.delete('0.0', END)
    word_text.insert('0.0', text)

    # Destroy the Listbox if it's currently displayed
    if entry.lb_up:
        entry.lb.destroy()
        entry.lb_up = False
def pronounce(event):
   engine=pyttsx3.init()
   engine.say(word)
   engine.runAndWait()
def search_by_prefix():
    prefix = prefix_entry.get()
    suggestions = []
    trie.findAll(trie.root, prefix, suggestions)
    complete_suggestions = [word for word in suggestions if trie.search(word)]
    prefix_text.delete('0.0', END)
    prefix_text.insert('0.0', '\n'.join(complete_suggestions))
def search_by_suffix():
   suffix=suffix_entry.get()
   suggestions=[]
   for word in NWORDS.keys():
       if word.endswith(suffix):
           suggestions.append(word)
   suffix_text.delete('0.0',END)
   suffix_text.insert('0.0','\n'.join(suggestions))
if __name__=='__main__':
   PROGRAM_NAME="Dictionary"
   root=Tk()
   root.geometry('800x600')
   root.title(PROGRAM_NAME)
   frame1=Frame(root)
   frame1.pack()
   entry=AutocompleteEntry(frame1)
   entry.pack(side=LEFT)
   button=Button(frame1,text='Search',width=25,command=showSearchResults)
   button.pack(side=LEFT)
   entry.focus()
   language_var=StringVar(value="en")
   language_options=["en","es","fr","de","it"]
   language_menu=OptionMenu(frame1,language_var,*language_options)
   language_menu.pack(side=LEFT)
   word_text=Text(root,wrap='word',height=5)
   word_text.pack(expand='yes',fill='both')
   prefix_frame=Frame(root)
   prefix_frame.pack(pady=10)
   prefix_label=Label(prefix_frame,text="Search by Prefix:")
   prefix_label.pack(side=LEFT)
   prefix_entry=Entry(prefix_frame)
   prefix_entry.pack(side=LEFT)
   prefix_button=Button(prefix_frame,text="Search",command=search_by_prefix)
   prefix_button.pack(side=LEFT)
   prefix_text=Text(root,wrap='word',height=5)
   prefix_text.pack(expand='yes',fill='both')
   suffix_frame=Frame(root)
   suffix_frame.pack(pady=10)
   suffix_label=Label(suffix_frame,text="Search by Suffix:")
   suffix_label.pack(side=LEFT)
   suffix_entry=Entry(suffix_frame)
   suffix_entry.pack(side=LEFT)
   suffix_button=Button(suffix_frame,text="Search",command=search_by_suffix)
   suffix_button.pack(side=LEFT)
   suffix_text=Text(root,wrap='word',height=5)
   suffix_text.pack(expand='yes',fill='both')
   root.mainloop()




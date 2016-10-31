Presentation
############


 * **Pirus** ( PIpeline RUnner Service) is a tool to manage installation and execution of informatic pipelines.
 * Stand alone project
 * Sub project of Regovar



Goals of Pirus
==============
Pirus aimed at performing computing tasks taking as input files to produce results in the form of one or more files. 
First devised in order to perform bioinformatic pipelines as part of research and or medical diagnostics, 
Pirus is for both computer scientists developing these pipelines, as system administrators to ensure the computer server maintenance, 
that to end users. 


*Each of them have different needs :*

.. image:: https://raw.githubusercontent.com/REGOVAR/Pirus/master/docs/img/0032.1.png
 
+-------------------------------------------------------------+------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------+
| Sys administrator                                           | Bio informaticien                                                | Clinician                                                                                                | 
+=============================================================+==================================================================+==========================================================================================================+ 
| * No way they install anything on the server                | * I want to do all I want                                        | * I don't want to see any command line                                                                   | 
| * I don't want to struggle with theirs weirds dependancies  | * I want to use all softwares I wants (and I choose the version) | * I just want to click a button to get my results                                                        | 
| * Deployement shall be easy                                 | * No time to spent on a endusers graphical interface             | * I'm interruptable, I do many things at the same time, I don't want to be stuck when waiting my results | 
+-------------------------------------------------------------+------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------+ 

**Yes ! The solution exists ! Pirus !**

.. image:: https://raw.githubusercontent.com/REGOVAR/Pirus/master/docs/img/0032.2.png


Features
========
 * Deployement with `pip install` [TODO]
 * All in one product (server application, client web interface)
 * One simple config file
 * No exotics depencies, no weird customizations
 * Virtual environment for pipeline execution (LXD container)
 * API REST
 * Easy to create a custom pipeline (few technical constraints)
 * Resumable upload for big files
 * Possibility to expose a simple interface to setup a pipeline (according to a unique json file)
 * Push notification for Run progress
 * Mail notification for Run status changed (when finished or when an error occured by example) [TODO]
 * Run can be paused, resumed and canceled

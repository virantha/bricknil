Two buttons on port 0 and 1

* Port 0 - Left side
* Port 1 - Right side

Modes and returned values:
   # *rckey*
      * 0 = Nothing pressed
      * 1 = '+' button pushed
      * 255 = '-' button pushed
      * 127 = 'red' button pushed

   # *keyr* same
   # *keya* same

   # *keyd* - 
      * 0 = Nothing pressed
      * 1 = '+'
      * 2 = red
      * 4 = '-'
        
   # *keysd*  bitmask (can tell when multiple buttons are being pressed)
      * [0,0,0] = Nothing pressed
      * [1,0,0] = '+'
      * [0,1,0] = red
      * [0,0,1] = '-'

::

    {0: {'id': 55,
         'input': True,
         'modes': {0: {'dataset_decimals': 0,
                       'dataset_total_figures': 2,
                       'dataset_type': '8b',
                       'datasets': 1,
                       'input': True,
                       'name': 'RCKEY'},
                   1: {'dataset_decimals': 0,
                       'dataset_total_figures': 2,
                       'dataset_type': '8b',
                       'datasets': 1,
                       'input': True,
                       'name': 'KEYA '},
                   2: {'dataset_decimals': 0,
                       'dataset_total_figures': 2,
                       'dataset_type': '8b',
                       'datasets': 1,
                       'input': True,
                       'name': 'KEYR '},
                   3: {'dataset_decimals': 0,
                       'dataset_total_figures': 1,
                       'dataset_type': '8b',
                       'datasets': 1,
                       'input': True,
                       'name': 'KEYD '},
                   4: {'dataset_decimals': 0,
                       'dataset_total_figures': 1,
                       'dataset_type': '8b',
                       'datasets': 3,
                       'input': True,
                       'name': 'KEYSD'}},
         'name': 'Remote Button'},
     1: {'id': 55,
         'input': True,
         'modes': {0: {'dataset_decimals': 0,
                       'dataset_total_figures': 2,
                       'dataset_type': '8b',
                       'datasets': 1,
                       'input': True,
                       'name': 'RCKEY'},
                   1: {'dataset_decimals': 0,
                       'dataset_total_figures': 2,
                       'dataset_type': '8b',
                       'datasets': 1,
                       'input': True,
                       'name': 'KEYA '},
                   2: {'dataset_decimals': 0,
                       'dataset_total_figures': 2,
                       'dataset_type': '8b',
                       'datasets': 1,
                       'input': True,
                       'name': 'KEYR '},
                   3: {'dataset_decimals': 0,
                       'dataset_total_figures': 1,
                       'dataset_type': '8b',
                       'datasets': 1,
                       'input': True,
                       'name': 'KEYD '},
                   4: {'dataset_decimals': 0,
                       'dataset_total_figures': 1,
                       'dataset_type': '8b',
                       'datasets': 3,
                       'input': True,
                       'name': 'KEYSD'}},
         'name': 'Remote Button'},

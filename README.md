 # springer-dl #
Script that should help to download all kinds of content from [http://rd.springer.com](rd.springer.com). This will sometime include books, journals, etc.

## Current state ##
It's a work in progress for now. The only thing that works now is to download books (e.g. [Book "Theoretische Informatik"](http://rd.springer.com/book/10.1007/978-3-8348-9853-1/page/1)).

## What it does ##
Using `springer-dl.py http://rd.springer.com/book/10.1007/978-3-8348-9853-1/page/1 TI.pdf` will start the download of each chapter and cover of the given book. After the download it will merge it into one single file `TI.pdf`.

## What it needs ##
- Python 3.x (I used 3.3 while developing it, not yet testet with other versions!)
- pdftk (for the merge process)
- imagemagick (to convert covers into PDF files)
- beautifulsoup4 & requests (see requirements.txt)

## Todo ##
- support journals
- allow multiple URLs at once
- better user feedback
- better error handling
- support more tools (instead of only pdftk and imagemagick)
- proxy support
- some way to allow the user to log-in (I don't need that as I'm logged in automatically while browsing from university's network)
- Python 2.x support
- look out for TODO comments ;-)

## License ##
see UNLICENSE

s=open('base.html').read();css=open('uh.css').read();js=open('uh.js').read()+'\n'+open('uh2.js').read()
i=s.index('</style>');s=s[:i]+css+s[i:]
a="if(!loadWork())seedWork();\nrender();\n</script>";assert s.count(a)==1
s=s.replace(a,js+"\nif(!loadWork())seedWork();\nrender();\n</script>")
open('atlas-console-book-view.html','w').write(s)

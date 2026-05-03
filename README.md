🔧 LR(0) Parser Generator & Visualizer

An interactive tool for building and visualizing LR(0) parsers from context-free grammars

Features • Installation • Usage • Examples • Documentation • Contributing
</div>
📋 Overview

The LR(0) Parser Generator is a desktop application that automatically constructs LR(0) parsers from any context-free grammar you provide. Instead of manually building item sets, calculating closures, and drawing DFA diagrams (which is tedious and error-prone), this tool does all the heavy work for you.
What is an LR(0) Parser?

LR(0) parsers are bottom-up shift-reduce parsers that form the foundation of more advanced parsing techniques (SLR(1), LR(1), LALR(1)). They read input from left to right and produce a rightmost derivation in reverse.
Why Use This Tool?

    🎓 Learn LR Parsing - Visualize how item sets and DFA states are constructed

    🔧 Quick Prototyping - Test grammars and identify conflicts instantly

    📊 Educational Resource - Perfect for compiler design courses and self-study

✨ Features
Core Functionality
Feature	Description
📝 Grammar Input	Enter any context-free grammar with support for alternatives (|) and epsilon (ε)
🔄 Augmented Grammar	Automatically adds S' → S start symbol
📚 Item Set Construction	Computes CLOSURE and GOTO operations
🏗️ DFA Generation	Builds complete LR(0) automaton
📊 Parsing Tables	Generates ACTION and GOTO tables
⚠️ Conflict Detection	Identifies shift-reduce and reduce-reduce conflicts
Visualization
Feature	Description
🖼️ DFA Rendering	Clear, textbook-style state diagrams
🔗 Transition Arrows	Smooth Bézier curves with distinct paths
🏷️ Item Display	Dot notation for LR(0) items
🎨 Color Coding	Accept states highlighted in red
🔍 Interactive Controls	Zoom, pan, and fit-to-view
User Interface
Feature	Description
📁 Example Grammars	Built-in examples (arithmetic, parentheses, etc.)
📋 Parsing Table View	Color-coded ACTION/GOTO tables
🐛 Error Reporting	Clear syntax error messages
💾 Cross-Platform	Works on Windows, macOS, and Linux

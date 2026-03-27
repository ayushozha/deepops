#!/usr/bin/env ruby

require "pathname"

python = ENV.fetch("PYTHON", "python")
script = Pathname.new(__dir__).join("../render_task_views.py").expand_path
target = ARGV[0] || Pathname.new(__dir__).join("..").expand_path.to_s

exec python, script.to_s, target

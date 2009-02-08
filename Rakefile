require "rake"

PYTHON_ENV = "env PYTHONPATH=."
PYTHON = "#{PYTHON_ENV} python"
PYTHON_FILES = Dir.glob("**/*.py")
PYLINT = [
  PYTHON_ENV,
  `which pylint`.strip(),
  "--output-format=parseable",
  "--reports=n",
  "--include-ids=y",
  "--required-attributes=",
  "--module-rgx='[a-zA-Z_][a-zA-Z0-9_]*'",
  "--const-rgx='[a-zA-Z_][a-zA-Z0-9_]*'",
  "--argument-rgx='[a-z][a-zA-Z0-9_]*'",
  "--attr-rgx='[_a-z][a-zA-Z0-9_]*'",
  "--method-rgx='[a-z_][a-zA-Z0-9_]*'",
  "--function-rgx='[a-z_][a-zA-Z0-9_]*'",
  "--variable-rgx='[a-z_][a-zA-Z0-9_]*'",
  "--class-rgx='[A-Z_][a-zA-Z0-9_]*'",
  "--disable-msg=W0612,R0904,R0201,I0011,",
  "",
].join(" ")

do_test = proc do |spec|
    match = /^test:([^:]+):?(.+)?$/.match(spec)
    if match
        file, tests = *match.captures
        system("#{PYTHON} #{file} #{tests}")
    end
    $0
end

desc "Specific tests"
task "test:my/testmod.py[:TestClass[.testMethod]]" do
    # dummy task just to get some usage with rake -T
end

rule(/^test:/ => [do_test]) do
    # no-op
end

task :default => :test

desc "Pylint."
task :pylint do
    system("#{PYLINT} #{PYTHON_FILES.join(" ")}  2>/dev/null ")
end

desc "Unit tests."
task :test do
    cmd = "#{PYTHON} test/tests.py"
    system(cmd) or fail("Tests failed!")
    Rake::Task[:pylint].invoke
end

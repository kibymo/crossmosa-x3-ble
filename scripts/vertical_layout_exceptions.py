"""Allow local allocation recovery in vertical layout, without enabling it globally."""
Import("env")


def vertical_layout_object(build_env, node):
    local = build_env.Clone()
    local.ProcessUnFlags("-fno-exceptions")
    local.AppendUnique(CXXFLAGS=["-fexceptions"])
    return local.Object(node)


env.AddBuildMiddleware(vertical_layout_object, "*/ParsedTextVertical.cpp")

cmake_minimum_required(VERSION 3.22)
project(TGZenerRack VERSION 1.1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
FetchContent_Declare(juce
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG 8.0.17-security
    GIT_SHALLOW TRUE)
FetchContent_MakeAvailable(juce)

juce_add_plugin(TGZenerRack
    COMPANY_NAME "Independent Audio"
    BUNDLE_ID "audio.independent.tgzener"
    PLUGIN_MANUFACTURER_CODE Iaud
    PLUGIN_CODE Tgz1
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE
    FORMATS VST3
    PRODUCT_NAME "TG Zener Rack")

juce_add_binary_data(TGZenerMeasurementData
    SOURCES
      reference/TGZener4Freq_THD2pct_InputScaled.bin
      Assets/faceplate.png
      Assets/knob_red.png
      Assets/knob_blue.png
      Assets/button_on.png
      Assets/button_off.png)

target_sources(TGZenerRack PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginProcessor.h
    Source/PluginEditor.cpp
    Source/PluginEditor.h
    Source/TGFastZenerLimiter.h
    Source/TGReferenceGrid.h)

target_compile_definitions(TGZenerRack PRIVATE
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0)

target_link_libraries(TGZenerRack PRIVATE
    TGZenerMeasurementData
    juce::juce_audio_utils
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags)

include(CTest)
if(BUILD_TESTING)
    foreach(test_name IN ITEMS basic controls program autotrack detector_clean spectra embedded_memory)
        add_executable(tg_test_${test_name} tests/test_${test_name}.cpp)
        target_compile_features(tg_test_${test_name} PRIVATE cxx_std_17)
        add_test(NAME tg_${test_name}
            COMMAND tg_test_${test_name}
                "${CMAKE_CURRENT_SOURCE_DIR}/reference/TGZener4Freq_THD2pct_InputScaled.bin")
    endforeach()
endif()

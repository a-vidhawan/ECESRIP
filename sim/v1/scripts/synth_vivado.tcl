# =============================================================================
# synth_vivado.tcl
# =============================================================================
# Xilinx Vivado synthesis script for hopfield_top.
#
# Usage
# -----
#   vivado -mode batch -source scripts/synth_vivado.tcl
#
# Outputs (in ./vivado_out/)
#   *.dcp      — design checkpoint (post-synthesis)
#   *.rpt      — utilization and timing reports
#   *.bit      — bitstream (if impl_and_bit = 1)
#
# Configuration
# -------------
# Edit the variables in the "User settings" section below.
# =============================================================================

# ---- User settings ----------------------------------------------------------
set part        "xc7a35tcpg236-1"    ;# Artix-7 35T (change as needed)
set top_module  "hopfield_top"
set N           8                    ;# Must match the generated RTL
set out_dir     "./vivado_out"
set impl_and_bit 0                   ;# Set to 1 to run impl + bitstream

# Source files (add neuron_logic_generated.sv once pipeline has run)
set rtl_files {
    rtl/weight_rom.sv
    rtl/neuron_bank.sv
    rtl/update_ctrl.sv
    rtl/hopfield_top.sv
}
# Uncomment after running pipeline:
# lappend rtl_files "build_${N}/rtl/neuron_logic_generated.sv"

# Constraint file (create rtl/hopfield_top.xdc for your board)
set xdc_file    "rtl/hopfield_top.xdc"
# -----------------------------------------------------------------------------

# Create output directory
file mkdir $out_dir

# Create project in memory
create_project -in_memory -part $part

# Set SystemVerilog language
set_property default_lib work [current_project]
set_property target_language SystemVerilog [current_project]

# Add RTL sources
foreach f $rtl_files {
    if {[file exists $f]} {
        add_files -norecurse $f
        set_property FILE_TYPE {SystemVerilog} [get_files $f]
    } else {
        puts "WARNING: source file not found: $f"
    }
}

# Add constraints if present
if {[file exists $xdc_file]} {
    add_files -fileset constrs_1 $xdc_file
} else {
    puts "WARNING: No XDC constraint file found at $xdc_file"
}

# Set top module
set_property top $top_module [current_fileset]

# Synthesis options
set_property STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY rebuilt \
    [get_runs synth_1]

# Run synthesis
puts "Running synthesis …"
synth_design \
    -top       $top_module \
    -part      $part       \
    -mode      out_of_context

# Reports
report_utilization -file "$out_dir/${top_module}_utilization.rpt"
report_timing_summary -file "$out_dir/${top_module}_timing.rpt"

# Save checkpoint
write_checkpoint -force "$out_dir/${top_module}_synth.dcp"
puts "Synthesis complete.  Checkpoint: $out_dir/${top_module}_synth.dcp"

# ---- Implementation + bitstream (optional) ----------------------------------
if {$impl_and_bit} {
    puts "Running implementation …"
    opt_design
    place_design
    route_design
    report_timing_summary -file "$out_dir/${top_module}_routed_timing.rpt"
    write_checkpoint -force "$out_dir/${top_module}_routed.dcp"
    write_bitstream -force "$out_dir/${top_module}.bit"
    puts "Bitstream: $out_dir/${top_module}.bit"
}

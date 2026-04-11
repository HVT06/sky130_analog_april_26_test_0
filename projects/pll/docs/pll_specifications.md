# PLL Specifications — Ring-Oscillator PLL, Sky130A

## 1. System-Level Specifications

| Parameter                 | Min    | Typ    | Max    | Unit    | Notes                            |
|---------------------------|--------|--------|--------|---------|----------------------------------|
| **VCO Frequency Range**   | 40     | 275    | 550    | MHz     | All 16 coarse bands combined     |
| **Reference Clock Freq**  | 1      | 50     | 100    | MHz     | ua[0] input                      |
| **Feedback Divider N**    | 1      | —      | 255    | —       | 8-bit programmable via ui[7:0]   |
| **Output Divider M**      | 2      | —      | 256    | —       | 3-bit select via uio[2:0]       |
| **Output Freq (ua[1])**   | 0.195  | —      | 275    | MHz     | fvco / M                         |
| **Loop Bandwidth**        | 0.3    | 2      | 5      | MHz     | Varies with N                    |
| **Phase Margin**          | 55     | 65     | —      | deg     | Stability criterion              |
| **Lock Time**             | —      | 5      | 10     | µs      | To ±1% frequency error           |
| **Supply Voltage (VDD)**  | 1.62   | 1.80   | 1.98   | V       | ±10% tolerance                   |
| **Total Power**           | —      | 3.0    | 5.0    | mW      | At 500 MHz, all blocks active    |
| **Temperature Range**     | -40    | 27     | 125    | °C      | Industrial range                 |

## 2. VCO Specifications

| Parameter                    | Min    | Typ    | Max    | Unit      |
|------------------------------|--------|--------|--------|-----------|
| **Topology**                 | —      | 5-stage current-starved ring | — | —  |
| **Coarse Bands**             | —      | 16     | —      | bands     |
| **Coarse Band Step**         | 25     | 30     | 40     | MHz       |
| **Fine Tune Range per Band** | 25     | 35     | 50     | %         |
| **Kvco (fine)**              | 150    | 300    | 500    | MHz/V     |
| **Supply Pushing (Kpush)**   | —      | 30     | 50     | MHz/V     |
| **Phase Noise @1MHz offset** | —      | -85    | -75    | dBc/Hz    |
| **Phase Noise @10MHz offset**| —      | -105   | -95    | dBc/Hz    |
| **Core Power**               | —      | 1.5    | 2.5    | mW        |

### 2.1 VCO Transistor Sizes

| Device          | Type  | W (µm)  | L (µm)  | Multiplier | Per  |
|-----------------|-------|---------|---------|------------|------|
| M_p_drive       | pfet  | 2.0     | 0.15    | 1          | stage|
| M_n_drive       | nfet  | 1.0     | 0.15    | 1          | stage|
| M_p_bias_unit   | pfet  | 4.0     | 1.0     | 1          | stage|
| M_n_bias_unit   | nfet  | 2.0     | 1.0     | 1          | stage|
| M_p_coarse[0]   | pfet  | 0.5     | 1.0     | 1          | global|
| M_p_coarse[1]   | pfet  | 1.0     | 1.0     | 1          | global|
| M_p_coarse[2]   | pfet  | 2.0     | 1.0     | 1          | global|
| M_p_coarse[3]   | pfet  | 4.0     | 1.0     | 1          | global|
| M_n_coarse[0]   | nfet  | 0.25    | 1.0     | 1          | global|
| M_n_coarse[1]   | nfet  | 0.5     | 1.0     | 1          | global|
| M_n_coarse[2]   | nfet  | 1.0     | 1.0     | 1          | global|
| M_n_coarse[3]   | nfet  | 2.0     | 1.0     | 1          | global|
| C_var (varactor) | nfet | 1.0     | 1.0     | 1          | node |

### 2.2 Node Capacitances (Estimated)

| Node              | Cgate  | Cvar   | Cwire  | Ctotal  | Unit |
|-------------------|--------|--------|--------|---------|------|
| VCO stage output  | 3      | 50-100 | 5      | 58-108  | fF   |

## 3. PFD Specifications

| Parameter                | Value    | Unit    | Notes                         |
|--------------------------|----------|---------|-------------------------------|
| Topology                 | Tri-state, edge-triggered | — | Two D-FFs + AND reset  |
| Dead zone elimination    | Yes      | —       | 4-inverter reset delay        |
| Min detectable phase err | < 50     | ps      | ~1% of 5 ns period           |
| Reset pulse width        | 200-400  | ps      | Set by delay chain            |
| Max operating freq       | 600      | MHz     | > max fvco/N                  |
| Transistor W (NMOS)      | 0.42     | µm      | L = 150 nm                    |
| Transistor W (PMOS)      | 0.84     | µm      | L = 150 nm (2× NMOS)         |

## 4. Charge Pump Specifications

| Parameter             | Min   | Typ   | Max   | Unit  | Notes                     |
|-----------------------|-------|-------|-------|-------|---------------------------|
| Pump current (Icp)    | 9     | 10    | 11    | µA    | Nominal bias              |
| Current mismatch      | —     | 2     | 5     | %     | |Iup - Idn| / Icp        |
| Output compliance     | 0.3   | —     | 1.5   | V     | Valid Vctrl range         |
| Leakage current       | —     | —     | 100   | pA    | When both switches off    |

### 4.1 CP Transistor Sizes

| Device       | Type  | W (µm) | L (µm) | Notes               |
|-------------|-------|---------|---------|---------------------|
| M_up_sw     | pfet  | 2.0     | 0.50    | UP switch            |
| M_dn_sw     | nfet  | 1.0     | 0.50    | DN switch            |
| M_bias_p    | pfet  | 4.0     | 1.0     | PMOS current mirror  |
| M_bias_n    | nfet  | 2.0     | 1.0     | NMOS current mirror  |
| M_ref       | nfet  | 2.0     | 1.0     | Reference branch     |

## 5. Loop Filter Specifications

| Parameter   | Value   | Unit  | Notes                          |
|-------------|---------|-------|--------------------------------|
| R           | 680     | Ω     | Poly resistor (res_high_po)    |
| C₁          | 120     | pF    | MIM cap (cap_mim_m3_1)        |
| C₂          | 12      | pF    | MOS gate cap                   |
| ωz (zero)   | 2π×2.0  | Mrad/s| 1/(R·C₁)                      |
| ωp2 (pole)  | 2π×20   | Mrad/s| (C₁+C₂)/(R·C₁·C₂)            |

## 6. Divider Specifications

### 6.1 Feedback Divider /N

| Parameter           | Value       | Notes                          |
|--------------------|-------------|--------------------------------|
| Division range     | 1 to 255    | 8-bit control via ui[7:0]     |
| Architecture       | ÷2 chain + MUX | 8 TSPC/static FF stages   |
| Max input freq     | 600 MHz     | First stage = TSPC FF         |
| First-stage W_n    | 0.84 µm     | TSPC optimised for speed      |
| First-stage W_p    | 1.68 µm     | 2× ratio                      |
| Later stages       | standard    | Static CMOS dividers          |

### 6.2 Output Divider /M

| Parameter           | Value            | Notes                      |
|--------------------|------------------|----------------------------|
| Division options   | 2,4,8,16,32,64,128,256 | 3-bit MUX select    |
| Control            | uio[2:0]         | See design doc §8.2        |
| Max input freq     | 600 MHz          | Same TSPC first stage      |

## 7. Lock Detector Specifications

| Parameter              | Value   | Unit   | Notes                       |
|------------------------|---------|--------|-----------------------------|
| Detection method       | XOR + LPF | —   | Phase error below threshold |
| Lock threshold         | ±5      | %      | Of reference period         |
| Filter time constant   | 1       | µs     | Prevents false lock         |
| Output                 | uo[0]   | —      | Active high when locked     |

## 8. Technology Parameters (Sky130A)

| Parameter           | Value                          | Notes                 |
|--------------------|--------------------------------|-----------------------|
| PDK                | sky130A (open_pdks)            | 130nm node            |
| NMOS model         | sky130_fd_pr__nfet_01v8        | 1.8V regular Vt      |
| PMOS model         | sky130_fd_pr__pfet_01v8        | 1.8V regular Vt      |
| VDD                | 1.8 V                          | Nominal               |
| Min L              | 150 nm                         | For digital logic     |
| Process corners    | TT, FF, SS, SF, FS            | 5 corners             |
| Temperatures       | -40, 27, 125 °C               | 3 temperatures        |

## 9. Interface Summary

| Pin Group   | Pins       | Direction | Function                        |
|-------------|------------|-----------|----------------------------------|
| ua[0]       | 1 analog   | Input     | Reference clock                  |
| ua[1]       | 1 analog   | Output    | Divided VCO output (scope obs.)  |
| ui[7:0]     | 8 digital  | Input     | Feedback divider ratio N         |
| uio[2:0]    | 3 digital  | Input     | Output divider select M          |
| uio[6:3]    | 4 digital  | Input     | VCO coarse band select           |
| uio[7]      | 1 digital  | Input     | PLL enable (active high)         |
| uo[0]       | 1 digital  | Output    | Lock detect                      |
| uo[1]       | 1 digital  | Output    | Feedback divider monitor         |
| uo[2]       | 1 digital  | Output    | VCO direct output (buffered)     |
| uo[3..7]    | 5 digital  | Output    | Reserved (tied low)              |

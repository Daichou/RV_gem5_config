
CC:=riscv64-unknown-elf-gcc
exe:=dhrystone
obj:=dhrystone_main.o dhrystone.o
CFLAGS:= -march=rv64ima -mabi=lp64
all:$(obj)
	$(CC) $(CFLAGS) -o $(exe) $(obj)
%.o:%.c
	$(CC) $(CFLAGS) -c $^ -o $@

.PHONY:clean
clean:
	rm -rf $(obj) $(exe)

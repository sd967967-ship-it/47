/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.twosum;

/**
 *
 * @author sd967
 */
import java.util.*;
public class Twosum {
    
    int n;
    int target=0;
    int sum=0;
    int arr[];
    int c=0;//counter
     Scanner in=new Scanner(System.in);
    public Twosum(int size)
    {
        this.n=size;
        this.arr=new int[n];
    }
    void input()
    {
        
        System.out.println("enter array");
        for(int i=0;i<arr.length;i++)
        {
            arr[i]=in.nextInt();
        }
        System.out.println("enter target");
        target=in.nextInt();
        
    }
    void compute()//finding element with the number that make target
    {
        for(int i=0;i<arr.length;i++)
        {
            for (int j = i+1; j < arr.length; j++) {
                sum=arr[i]+arr[j];
                        if(sum==target)
                        {
                            c++;
                            System.out.println("sum found from positions "+ i +" "+j);
                        }
            }
        }
        if(c==0)
            System.out.println("no positions could form output");
    }

    public static void main(String[] args) {
        System.out.println("enter size of array");
        Scanner in=new Scanner(System.in);
        int size=in.nextInt();
        
        Twosum ob=new Twosum(size);
        ob.input();
        ob.compute();
        
    }
}
